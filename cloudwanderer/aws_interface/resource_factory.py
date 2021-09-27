from typing import List, Optional

from boto3 import resource
from boto3.resources.collection import CollectionManager
from .boto3_loaders import ServiceMappingLoader
from boto3.resources.base import ResourceMeta, ServiceResource
from boto3.resources.factory import ResourceFactory
import logging
from ..exceptions import UnsupportedResourceTypeError

from boto3.resources.model import Collection, ResourceModel
from boto3.utils import ServiceContext
from botocore import xform_name

logger = logging.getLogger(__name__)


class CloudWandererResourceFactory(ResourceFactory):
    """Enriches functionality of boto3 resource objects with CloudWanderer specific methods."""

    def __init__(self, emitter, service_mapping_loader: ServiceMappingLoader):
        super().__init__(emitter=emitter)
        self.service_mapping_loader = service_mapping_loader

    def load_from_definition(self, resource_name, single_resource_json_definition, service_context):

        # Using the loaded JSON create a ResourceModel object.
        resource_model = ResourceModel(
            resource_name, single_resource_json_definition, service_context.resource_json_definitions
        )
        attrs = {}
        # CloudWanderer resource methods
        self._load_cloudwanderer_methods(
            attrs=attrs, resource_name=resource_name, resource_model=resource_model, service_context=service_context
        )

        # CloudWanderer resource properties
        self._load_cloudwanderer_properties(
            attrs=attrs, resource_name=resource_name, resource_model=resource_model, service_context=service_context
        )
        class_definition = super().load_from_definition(resource_name, single_resource_json_definition, service_context)
        for attribute_name, attribute_value in attrs.items():
            setattr(class_definition, attribute_name, attribute_value)
        return class_definition

    def _load_cloudwanderer_methods(self, attrs, resource_name, resource_model, service_context) -> None:
        if service_context.service_name != xform_name(resource_name):
            # This should only exist only exist on Resources, not on Services
            attrs["get_discovery_action_templates"] = self._create_get_discovery_action_templates()
        attrs["get_collection_manager"] = self._create_get_collection_manager()
        attrs["get_collection_model"] = self._create_get_collection_model()
        attrs["get_subresource"] = self._create_get_subresource()

    def _create_get_discovery_action_templates(self):
        def get_discovery_action_templates(self, discovery_regions: List[str]):
            return self.resource_map.get_discovery_action_templates(discovery_regions=discovery_regions)

        return get_discovery_action_templates

    def _create_get_collection_manager(self):
        def get_collection_manager(self, resource_type=str) -> CollectionManager:
            collection_model = self.get_collection_model(resource_type=resource_type)
            return getattr(self, collection_model.name)

        return get_collection_manager

    def _create_get_collection_model(self):
        def get_collection_model(self, resource_type) -> Optional[str]:
            """Resource names *almost* always match their resource type, but not always.
            I'm looking at you EC2 KeyPair!

            A resource _name_ is the PascalCase key it has in the ``resources`` dict in the service definition json.
            A resource _type_ is (in the argument to this method) a snake_case resource type which matches the resource name.
            A resource _type_ in boto3 is a PascalCase resource type used to associate a Collection (hasMany) with its
                resource definition.
            In order to identify a collection we need to:
                1. Get the boto3 resource type of the resource which has the resource name that corresponse with the cloudwanderer resource type
                2. Lookup the collection that references that resource type.
                3. Return that collection name
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

    def _create_get_subresource(self):
        def get_subresource(self, resource_type: str, args: List[str] = None, empty_resource=False) -> ServiceResource:
            for resource in self.meta.resource_model.subresources:
                resource_name = xform_name(resource.name)
                if resource_name == resource_type:
                    if empty_resource:
                        args = ["" for _ in resource.resource.model.identifiers]
                    return getattr(self, resource.name)(*args)
            raise UnsupportedResourceTypeError(f"Could not find Boto3 subresource for {resource_type}")

        return get_subresource

    def _load_cloudwanderer_properties(
        self, attrs, resource_name, resource_model, service_context: ServiceContext
    ) -> None:
        attrs["service_name"] = service_context.service_name
        attrs["service_map"] = self.service_mapping_loader.get_service_mapping(
            service_name=service_context.service_name
        )

        if resource_name == service_context.service_name:

            @property
            def resource_types(self):
                resource_types = [
                    xform_name(collection.resource.type) for collection in self.meta.resource_model.collections
                ]

                return resource_types

            attrs["resource_types"] = resource_types
        else:
            attrs["resource_type"] = xform_name(resource_name)
            attrs["resource_map"] = attrs["service_map"].get_resource_map(boto3_resource_name=resource_name)
