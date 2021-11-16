"""AWS Interface specific model classes."""
from typing import Any, Dict, Iterator, List, NamedTuple, Optional

import botocore
import jmespath  # type: ignore
from boto3.resources.base import ServiceResource

from ..base import ServiceResourceTypeFilter
from ..models import RelationshipAccountIdSource, RelationshipDirection, RelationshipRegionSource
from ..utils import camel_to_snake, snake_to_pascal


class AWSResourceTypeFilter(ServiceResourceTypeFilter):
    """AWS Specific resource type filter.

    Allows specification of either botocore filters or jmespath filters.
    """

    service: str
    resource_type: str
    botocore_filters: Dict[str, Any]
    jmespath_filters: List[str]

    def __init__(
        self,
        service: str,
        resource_type: str,
        botocore_filters: Optional[Dict[str, Any]] = None,
        jmespath_filters: Optional[List[str]] = None,
    ) -> None:
        self.service = service
        self.resource_type = resource_type
        self.botocore_filters = botocore_filters or {}
        self.jmespath_filters = jmespath_filters or []

    def filter_jmespath(self, resources: List[ServiceResource]) -> Iterator[ServiceResource]:
        if not self.jmespath_filters:
            yield from resources
        for resource in resources:
            for filter in self.jmespath_filters:
                if jmespath.search(filter, [resource.meta.data]):
                    yield resource

    def __repr__(self) -> str:
        """Return an instantiable representation of this object."""
        return (
            "AWSResourceTypeFilter("
            f"service='{self.service}', "
            f"resource_type='{self.resource_type}', "
            f"botocore_filters={self.botocore_filters}, "
            f"jmespath_filters={self.jmespath_filters})"
        )


class ServiceMap(NamedTuple):
    """Specification for additional CloudWanderer specific metadata about a Boto3 service."""

    name: str
    resource_definition: dict
    global_service: bool
    global_service_region: str
    service_definition: dict

    @property
    def is_global_service(self) -> bool:
        """Return whether this service is a global service."""
        return self.global_service

    @property
    def is_default_service(self) -> bool:
        """Return True if this service has no definition and should return default values."""
        return self.service_definition == {}

    def get_resource_map(self, resource_type: str) -> "ResourceMap":
        """Return the resource map given a snake_case resource name.

        Arguments:
            resource_type: The snake_case name of the resource map to get.
        """
        boto3_resource_name = snake_to_pascal(resource_type)
        return ResourceMap.factory(
            service_map=self,
            name=boto3_resource_name,
            definition=self.resource_definition.get(boto3_resource_name, {}),
        )

    @classmethod
    def factory(cls, name: str, definition: dict) -> "ServiceMap":
        service_definition = definition.get("service", {})
        return cls(
            name=name,
            global_service=service_definition.get("globalService", False),
            global_service_region=service_definition.get("globalServiceRegion"),
            service_definition=service_definition,
            resource_definition=definition.get("resources", {}),
        )


class ResourceMap(NamedTuple):
    """Specification for additional CloudWanderer specific metadata about a Boto3 resource type.

    Attributes:
        name:
            The PascalCase name of the resource (e.g. ``Instance``)
        type:
            The snake_case type of the resource (e.g. ``instance``)
        region_request:
            An optional definition for how to perform a secondary query to
            discover the region in which this resource exists.
        default_aws_resource_type_filter:
           The default :class:`AWSResourceTypeFilter` for this resource.
        service_map:
            A link back to the parent :class:`ServiceMap` object.
        relationships:
            The specifications for the relationships this resource can have.
        secondary_attribute_maps:
            The specifications for the secondary attributes for this resource.
        urn_overrides:
            Optional specifications for overriding URN parts based on resource metadata.
        regional_resource:
            Whether or not this resource exists in every region.
        requires_load:
            If the resource requires .load() calling on it before it has a complete set of metadata.
            Used by IAM PolicyVersion because as a dependent resource it needs to be listed with ListPolicyVersions,
            then subsequently got with GetPolicyVersion.
    """

    name: str
    type: Optional[str]
    region_request: Optional["ResourceRegionRequest"]
    default_aws_resource_type_filter: AWSResourceTypeFilter
    service_map: ServiceMap
    relationships: List["RelationshipSpecification"]
    secondary_attribute_maps: List["SecondaryAttributeMap"]
    urn_overrides: List["IdPartSpecification"]
    regional_resource: bool = True
    requires_load: bool = False

    @classmethod
    def factory(
        cls,
        name: str,
        service_map: ServiceMap,
        definition: Dict[str, Any],
    ) -> "ResourceMap":
        return cls(
            name=name,
            type=definition.get("type"),
            region_request=ResourceRegionRequest.factory(definition.get("regionRequest")),
            regional_resource=definition.get("regionalResource", True),
            default_aws_resource_type_filter=AWSResourceTypeFilter(
                service=service_map.name,
                resource_type=botocore.xform_name(name),
                botocore_filters=definition.get("defaultBotocoreFilters", {}),
                jmespath_filters=definition.get("defaultJMESPathFilters", []),
            ),
            service_map=service_map,
            relationships=[
                RelationshipSpecification.factory(relationship_specification)
                for relationship_specification in definition.get("relationships", [])
            ],
            secondary_attribute_maps=[
                SecondaryAttributeMap(source_path=mapping["sourcePath"], destination_name=mapping["destinationName"])
                for mapping in definition.get("secondaryAttributeMaps", [])
            ],
            urn_overrides=[
                IdPartSpecification.factory(urn_override) for urn_override in definition.get("urnOverrides", [])
            ],
            requires_load=definition.get("requiresLoad", False),
        )

    def should_query_resources_in_region(self, region: str) -> bool:
        """Return whether this resource should be queried from this region.

        Arguments:
            region: The region in which to query the resource.
        """
        if not self.service_map.is_global_service:
            return True
        return self.service_map.is_global_service and self.service_map.global_service_region == region


class ResourceRegionRequest(NamedTuple):
    """Specification for a request to get a resource's region."""

    operation: str
    params: list
    path_to_region: str
    default_value: str

    @classmethod
    def factory(cls, definition: Optional[Dict[str, Any]]) -> Optional["ResourceRegionRequest"]:
        if not definition:
            return None
        return cls(
            operation=definition["operation"],
            params=[ResourceRegionRequestParam.factory(param) for param in definition["params"]],
            path_to_region=definition["pathToRegion"],
            default_value=definition["defaultValue"],
        )

    def build_params(self, resource: ServiceResource) -> dict:
        """Return the params required to query the resource's region from the Boto3 resource's attributes.

        Arguments:
            resource: The Boto3 Resource to build params for.
        """
        params = {}
        for param in self.params:
            params[param.target] = self._get_param_value(resource, param)
        return params

    def _get_param_value(self, resource: ServiceResource, param: "ResourceRegionRequestParam") -> Any:
        if param.source == "resourceAttribute":
            return getattr(resource, param.name)
        raise AttributeError(f"Invalid param source {param.source}")


class ResourceRegionRequestParam(NamedTuple):
    """Specification for a request param data model."""

    target: str
    source: str
    name: str

    @classmethod
    def factory(cls, definition: dict) -> "ResourceRegionRequestParam":
        return cls(target=definition["target"], source=definition["source"], name=definition["name"])


class RelationshipSpecification(NamedTuple):
    """Specification for a relationship between two resources."""

    base_path: str
    id_parts: List["IdPartSpecification"]
    service: str
    resource_type: str
    region_source: RelationshipRegionSource
    account_id_source: RelationshipAccountIdSource
    direction: RelationshipDirection

    @classmethod
    def factory(cls, definition) -> "RelationshipSpecification":
        return cls(
            base_path=definition["basePath"],
            direction=RelationshipDirection[camel_to_snake(definition["direction"])],
            id_parts=[IdPartSpecification.factory(id_part) for id_part in definition["idParts"]],
            service=definition["service"],
            resource_type=definition["resourceType"],
            region_source=RelationshipRegionSource[camel_to_snake(definition["regionSource"])],
            account_id_source=RelationshipAccountIdSource[camel_to_snake(definition["accountIdSource"])],
        )


class IdPartSpecification(NamedTuple):
    """Specification for getting the ID parts of a resource's relationship with another resource."""

    path: str
    regex_pattern: str

    @classmethod
    def factory(cls, definition) -> "IdPartSpecification":
        return cls(path=definition["path"], regex_pattern=definition.get("regexPattern", ""))


class SecondaryAttributeMap(NamedTuple):
    """Specification for mapping attributes contained in a secondary attribute to its parent's resource."""

    source_path: str
    destination_name: str
