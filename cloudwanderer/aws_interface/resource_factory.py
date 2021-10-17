"""Create the CloudWandererServiceResource objects that do the magic."""
import logging
import re
from typing import TYPE_CHECKING, Any, Callable, Dict, Generator, List, Optional
from unittest.mock import MagicMock

import jmespath
from boto3.resources.collection import CollectionManager
from boto3.resources.factory import ResourceFactory
from boto3.resources.model import Collection
from boto3.resources.params import create_request_parameters
from botocore import xform_name
from botocore.loaders import Loader
from botocore.model import Shape

from ..cloud_wanderer_resource import SecondaryAttribute
from ..exceptions import UnsupportedResourceTypeError
from ..models import Relationship, RelationshipAccountIdSource, RelationshipRegionSource, TemplateActionSet
from ..urn import URN, PartialUrn
from ..utils import snake_to_pascal
from .boto3_helpers import _clean_boto3_metadata
from .boto3_loaders import MergedServiceLoader, ServiceMap

if TYPE_CHECKING:
    from .session import CloudWandererBoto3Session
    from .stubs.resource import CloudWandererServiceResource
    from .stubs.service_context import ServiceContext


logger = logging.getLogger(__name__)


class CloudWandererResourceFactory(ResourceFactory):
    """Enriches functionality of boto3 resource objects with CloudWanderer specific methods."""

    def __init__(
        self,
        emitter,
        cloudwanderer_boto3_session: "CloudWandererBoto3Session",
        service_mapping_loader: Optional[Loader] = None,
    ) -> None:
        super().__init__(emitter=emitter)
        self.service_mapping_loader = service_mapping_loader or MergedServiceLoader()
        self.cloudwanderer_boto3_session = cloudwanderer_boto3_session

    def load_from_definition(self, resource_name, single_resource_json_definition, service_context) -> type:
        class_definition = super().load_from_definition(resource_name, single_resource_json_definition, service_context)
        attrs: Dict[str, Any] = {}
        # CloudWanderer resource methods
        self._load_cloudwanderer_methods(
            attrs=attrs,
            resource_name=resource_name,
            service_context=service_context,
            original_class_definition=class_definition,
        )

        # CloudWanderer resource properties
        self._load_cloudwanderer_properties(
            attrs=attrs,
            resource_name=resource_name,
            service_context=service_context,
        )

        for attribute_name, attribute_value in attrs.items():
            setattr(class_definition, attribute_name, attribute_value)
        return class_definition

    def _load_cloudwanderer_methods(
        self,
        attrs: Dict[str, Any],
        resource_name: str,
        service_context: "ServiceContext",
        original_class_definition: type,
    ) -> None:
        if service_context.service_name != xform_name(resource_name):
            # This should only exist only exist on Resources, not on Services
            attrs["get_discovery_action_templates"] = self._create_get_discovery_action_templates()
            attrs["get_dependent_resource"] = self._create_get_dependent_resource(service_context)
            if hasattr(original_class_definition, "load"):
                attrs["load"] = self._create_load(original_class_definition=original_class_definition)
        else:
            attrs["resource"] = self._create_resource()
        attrs["get_collection_manager"] = self._create_get_collection_manager()
        attrs["get_collection_model"] = self._create_get_collection_model()
        attrs["collection"] = self._create_collection_getter()
        attrs["get_account_id"] = self._create_get_account_id()
        attrs["get_urn"] = self._create_get_urn()
        attrs["get_region"] = self._create_get_region()
        attrs["get_secondary_attributes"] = self._create_get_secondary_attributes()

    def _create_load(self, original_class_definition: type) -> Callable:
        original_class_load = original_class_definition.load

        def load(self, *args) -> None:
            if not self.meta.resource_model.load:
                return
            identifiers = create_request_parameters(self, self.meta.resource_model.load.request)
            has_non_empty_values = any(list([x for x in identifiers.values()]))
            if not has_non_empty_values:
                logger.debug(
                    "Load is a noop on this %s %s because we are an empty_resource=True resource",
                    self.service_name,
                    self.resource_type,
                )
                return

            original_class_load(self)

        return load

    def _create_get_discovery_action_templates(self) -> Callable:
        def get_discovery_action_templates(self, discovery_regions: List[str]) -> List[TemplateActionSet]:
            """Return the discovery actions to be performed if getting this resource type in this region.

            Arguments:
                discovery_regions: The regions in which the query would be performed.
            """
            template_actions = []
            for discovery_region in discovery_regions:
                actions = TemplateActionSet([], [])
                if not self.resource_map.should_query_resources_in_region(discovery_region):
                    continue
                if self.service_map.is_global_service and self.resource_map.regional_resource:
                    cleanup_region = "ALL_REGIONS"
                else:
                    cleanup_region = discovery_region
                if self.resource_map.type != "dependentResource":
                    actions.get_urns.append(
                        PartialUrn(
                            cloud_name="aws",
                            service=self.service_map.name,
                            region=discovery_region,
                            resource_type=self.resource_type,
                        )
                    )
                actions.delete_urns.append(
                    PartialUrn(
                        cloud_name="aws",
                        service=self.service_map.name,
                        region=cleanup_region,
                        resource_type=self.resource_type,
                    )
                )
                template_actions.append(actions)
            return template_actions

        return get_discovery_action_templates

    def _create_get_collection_manager(self) -> Callable:
        def get_collection_manager(self, resource_type=str) -> CollectionManager:
            collection_model = self.get_collection_model(resource_type=resource_type)
            return getattr(self, collection_model.name)

        return get_collection_manager

    def _create_get_collection_model(self) -> Callable:
        def get_collection_model(self, resource_type) -> Optional[str]:
            """Resource names *almost* always match their resource type, but not always.

            I'm looking at you EC2 KeyPair!

            A resource _name_ is the PascalCase key it has in the ``resources`` dict in the service definition json.
            A resource _type_ is (in the argument to this method) a snake_case resource type which matches
                the resource name.
            A resource _type_ in boto3 is a PascalCase resource type used to associate a Collection (hasMany) with its
                resource definition.
            In order to identify a collection we need to:
                1. Get the boto3 resource type of the resource which has the resource name that corresponse with the
                    cloudwanderer resource type
                2. Lookup the collection that references that resource type.
                3. Return that collection name

            Arguments;
                resource_type: The snake case resource type to get a model for (e.g. ``'bucket'``)
            """
            boto3_resource_type = None
            for resource in self.meta.resource_model.subresources:
                # The key name in the resources dictionary in the service definition json
                resource_name = xform_name(resource.name)
                if resource_name == resource_type:
                    boto3_resource_type = resource.resource.type
                    break
            if not boto3_resource_type:
                raise UnsupportedResourceTypeError(f"Could not find Boto3 resource by the name {resource_type}")
            for collection_model in self.meta.resource_model.collections:
                if collection_model.resource.type == boto3_resource_type:
                    return collection_model
            raise UnsupportedResourceTypeError(f"Could not find Boto3 collection for {resource_type}")

        return get_collection_model

    def _create_resource(self) -> Callable:
        def resource(
            self, resource_type: str, identifiers: List[str] = None, empty_resource=False
        ) -> "CloudWandererServiceResource":
            """Get a Boto3 ServiceResource object for a resource that exists in this service.

            Specifying empty_resource=True will return a ServiceResource object which does not
            correspond to a specific resource in AWS but allows access to resource type metadata.
            """
            for resource in self.meta.resource_model.subresources:
                resource_name = xform_name(resource.name)
                if resource_name == resource_type:
                    if empty_resource:
                        identifiers = ["" for _ in resource.resource.model.identifiers]
                    return getattr(self, resource.name)(*identifiers)
            raise UnsupportedResourceTypeError(f"Could not find Boto3 resource for {resource_type}")

        return resource

    def _create_collection_getter(self) -> Callable:
        def collection(self, resource_type: str, filters: Optional[Dict[str, str]] = None) -> Collection:
            filters = filters or {}
            try:
                collection_model = self.get_collection_model(resource_type)
            except UnsupportedResourceTypeError:
                # If it's not a collection it might be a 'reference'
                for resource in self.meta.resource_model.references:
                    if resource.name == resource_type:
                        return getattr(self, resource.name)
                raise
            collection_model.name
            collection_manager = getattr(self, collection_model.name)
            return collection_manager.filter(**filters)

        return collection

    def _create_get_dependent_resource(factory_self, service_context: "ServiceContext") -> Callable:
        def get_dependent_resource(
            self, resource_type: str, args: List[str] = None, empty_resource=False
        ) -> "CloudWandererServiceResource":
            # We need to check for dependent resources in subresources and references to cover cases where the dependent
            # resource is only enumerable from the content of the parent resource (rather than a separate API call)
            # e.g. route_table > routes
            subresources_and_references = self.meta.resource_model.subresources + self.meta.resource_model.references
            for resource in subresources_and_references:
                resource_name = xform_name(resource.name)
                # references have snake_case names so let's make sure it's pascalcase
                pascal_resource_name = snake_to_pascal(resource_name)
                if resource_name == resource_type:
                    if empty_resource:

                        args = ["" for _ in range(len(resource.resource.model.identifiers))]
                        logger.debug("args: %s", args)
                        return factory_self.load_from_definition(
                            resource_name=pascal_resource_name,
                            single_resource_json_definition=service_context.resource_json_definitions.get(
                                pascal_resource_name
                            ),
                            service_context=service_context,
                        )(*args)

                    return getattr(self, resource.name)(*args)

            raise UnsupportedResourceTypeError(
                f"Could not find Boto3 subresource {resource_type} for {self.resource_type}."
            )

        return get_dependent_resource

    def _create_get_urn(self) -> Callable:
        def get_urn(self) -> URN:
            id_parts = [getattr(self, identifier) for identifier in self.meta.identifiers]
            return URN(
                account_id=self.get_account_id(),
                region=self.get_region(),
                service=self.service_name,
                resource_type=self.resource_type,
                resource_id_parts=id_parts,
            )

        return get_urn

    def _create_get_secondary_attributes(self) -> Callable:
        def get_secondary_attributes(self) -> Generator[SecondaryAttribute, None, None]:
            for secondary_attribute_name in self.secondary_attribute_names:
                getter = getattr(self, snake_to_pascal(secondary_attribute_name))
                secondary_attribute_resource = getter()
                secondary_attribute_resource.load()
                yield SecondaryAttribute(
                    secondary_attribute_name, **_clean_boto3_metadata(secondary_attribute_resource.meta.data)
                )

        return get_secondary_attributes

    def _create_secondary_attribute_names(self) -> Callable:
        @property  # type: ignore
        def secondary_attribute_names(self) -> List[SecondaryAttribute]:
            secondary_attribute_names = []
            for subresource in self.meta.resource_model.subresources:
                resource_map = self.service_map.get_resource_map(xform_name(subresource.name))
                logger.debug("ServiceResource get_secondary_attributes, subresource_name: %s", subresource.name)
                if not resource_map or resource_map.type != "secondaryAttribute":
                    continue
                secondary_attribute_names.append(xform_name(subresource.name))
            return secondary_attribute_names

        return secondary_attribute_names

    def _create_get_account_id(self) -> Callable:
        def get_account_id(self) -> str:
            return self.cloudwanderer_boto3_session.get_account_id()

        return get_account_id

    def _create_get_region(self) -> Callable:
        def get_region(self) -> str:
            if self.resource_map.region_request:
                method = getattr(self.meta.client, self.resource_map.region_request.operation)
                result = method(**self.resource_map.region_request.build_params(self))
                return (
                    jmespath.search(self.resource_map.region_request.path_to_region, result)
                    or self.resource_map.region_request.default_value
                )
            if self.service_map.global_service:
                return self.service_map.global_service_region

            return self.meta.client.meta.region_name

        return get_region

    def _create_normalized_raw_data(self) -> Callable[..., Dict[str, Any]]:
        @property  # type: ignore
        def normalized_raw_data(self) -> Dict[str, Any]:
            """Return the raw data dictionary for this resource, ensuring that all keys for this resource are present."""
            result = {attribute: None for attribute in self.shape.members.keys()}
            result.update(self.meta.data or {})
            return _clean_boto3_metadata(result)

        return normalized_raw_data

    def _create_resource_types(self) -> Callable[..., List[str]]:
        @property  # type: ignore
        def resource_types(self) -> List[str]:
            """Lists resources which are directly enumerable from the service"""
            resource_types = [
                xform_name(collection.resource.type) for collection in self.meta.resource_model.collections
            ]

            return resource_types

        return resource_types

    def _create_dependent_resource_types(self) -> Callable[..., List[str]]:
        @property  # type: ignore
        def dependent_resource_types(self) -> List[str]:
            dependent_resource_types = []
            for collection in self.meta.resource_model.collections:
                resource_type = xform_name(collection.resource.type)
                resource_map = self.service_map.get_resource_map(resource_type=resource_type)
                if resource_map.type == "dependentResource":
                    dependent_resource_types.append(resource_type)

            return dependent_resource_types

        return dependent_resource_types

    def _create_shape(self) -> Callable[..., Shape]:
        @property  # type: ignore
        def shape(self) -> Shape:
            service_model = self.meta.client.meta.service_model
            return service_model.shape_for(self.meta.resource_model.shape)

        return shape

    def _create_is_dependent_resource(self) -> Callable[..., bool]:
        def is_dependent_resource(self) -> bool:
            return self.resource_map.type == "dependentResource"

        return property(is_dependent_resource)

    def _create_relationships(self) -> Callable[..., Dict[str, Any]]:
        @property  # type: ignore
        def relationships(self) -> Dict[str, Any]:
            """Return PartialURNs for the relationships this resource has with other resources."""
            relationships = []
            for relationship_specification in self.resource_map.relationships:
                base_paths_raw = jmespath.search(relationship_specification.base_path, self.normalized_raw_data)
                base_paths = [base_paths_raw] if not isinstance(base_paths_raw, list) else base_paths_raw
                for base_path in base_paths:
                    if not base_path:
                        logger.debug("Skipping building a relationship for %s as the basePath is empty", self.get_urn())
                        continue
                    urn_args = {
                        "cloud_name": "aws",
                        "account_id": "unknown",
                        "region": "unknown",
                        "service": relationship_specification.service,
                        "resource_type": relationship_specification.resource_type,
                        "resource_id_parts": [],
                    }

                    if relationship_specification.account_id_source == RelationshipAccountIdSource.SAME_AS_RESOURCE:
                        urn_args["account_id"] = self.get_account_id()

                    if relationship_specification.region_source == RelationshipRegionSource.SAME_AS_RESOURCE:
                        urn_args["region"] = self.get_region()

                    for id_part in relationship_specification.id_parts:
                        id_raw = jmespath.search(id_part.path, base_path)
                        if not id_raw:
                            continue
                        if not id_part.regex_pattern:
                            urn_args["resource_id_parts"].append(id_raw)
                            continue
                        result = re.match(id_part.regex_pattern, id_raw)
                        for arg_name, arg_value in result.groupdict().items():
                            if arg_name in ["cloud_name", "account_id", "region", "service", "resource_type"]:
                                urn_args[arg_name] = arg_value
                                continue
                            if arg_name.startswith("id_part_"):
                                urn_args["resource_id_parts"].append(arg_value)
                    if not urn_args["resource_id_parts"]:
                        continue
                    relationships.append(
                        Relationship(partial_urn=PartialUrn(**urn_args), direction=relationship_specification.direction)
                    )
            return relationships

        return relationships

    def _load_cloudwanderer_properties(
        self, attrs: Dict[str, Any], resource_name: str, service_context: "ServiceContext"
    ) -> None:
        attrs["service_name"] = service_context.service_name
        attrs["service_map"] = ServiceMap.factory(
            name=service_context.service_name,
            definition=self.service_mapping_loader.load_service_model(
                service_name=service_context.service_name, type_name="resources-cw-1", api_version=None
            ),
        )
        attrs["cloudwanderer_boto3_session"] = self.cloudwanderer_boto3_session

        if resource_name == service_context.service_name:  # type: ignore
            # If it is a service:
            attrs["resource_types"] = self._create_resource_types()
        else:
            # If it is a resource:
            attrs["normalized_raw_data"] = self._create_normalized_raw_data()
            attrs["resource_type"] = xform_name(resource_name)
            attrs["resource_map"] = attrs["service_map"].get_resource_map(resource_type=xform_name(resource_name))
            attrs["dependent_resource_types"] = self._create_dependent_resource_types()
            attrs["secondary_attribute_names"] = self._create_secondary_attribute_names()
            attrs["shape"] = self._create_shape()
            attrs["relationships"] = self._create_relationships()
            attrs["is_dependent_resource"] = self._create_is_dependent_resource()
