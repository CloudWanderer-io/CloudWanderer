"""Boto3 Loaders.

Loaders and data classes to load custom CloudWanderer Boto3 service definitions and merge them with the boto3
provided ones. This allows cloudwanderer to extend Boto3 to support AWS resources that it does not support natively.
We can do this quite easily because CloudWanderer only needs a fraction of the functionality that native
Boto3 resources provide (i.e. the description of the resources).
"""

import json
import logging
import os
import pathlib
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

import boto3
import botocore
import jmespath  # type: ignore
from boto3.resources.base import ServiceResource
from botocore.exceptions import DataNotFoundError, UnknownServiceError  # type: ignore
from botocore.loaders import Loader

from ..cache_helpers import memoized_method
from ..exceptions import MalformedFileError, UnsupportedServiceError
from ..models import RelationshipAccountIdSource, RelationshipDirection, RelationshipRegionSource
from ..utils import camel_to_snake, snake_to_pascal

logger = logging.getLogger(__name__)


class CustomServiceLoader:
    """A class to load custom services."""

    def __init__(self, definition_path: str = "resource_definitions") -> None:
        self.service_definitions_path = os.path.join(pathlib.Path(__file__).parent.absolute(), definition_path)

    @memoized_method()
    def get_service_definition(self, service_name: str, type_name: str, api_version: str) -> dict:
        path = Path(service_name) / Path(api_version) / Path(f"{type_name}.json")
        full_path = self.service_definitions_path / path
        logger.debug("CustomServiceLoader get_service_definition loaded path %s", full_path)
        try:
            with open(full_path, "r") as file:
                return json.load(file)
        except FileNotFoundError:
            raise UnsupportedServiceError(f"{service_name} does not exist as a custom CloudWanderer service.")
        except json.decoder.JSONDecodeError as ex:
            raise MalformedFileError(f"{service_name} has an invalid file at {full_path}.") from ex

    def list_api_versions(self, service_name: str, type_name: str) -> List[str]:
        path = self.service_definitions_path / Path(service_name)
        try:
            api_versions = [
                d
                for d in os.listdir(path)
                if os.path.isdir(os.path.join(path, d)) and os.path.isfile(os.path.join(path, d, f"{type_name}.json"))
            ]
        except FileNotFoundError:
            raise UnsupportedServiceError(f"{service_name} does not exist as a custom CloudWanderer service.")

        return sorted(api_versions)

    @property
    def available_services(self) -> List[str]:
        """Return a list of available snake_case service names."""
        possible_services = [
            d
            for d in os.listdir(self.service_definitions_path)
            if os.path.isdir(os.path.join(self.service_definitions_path, d))
        ]
        return sorted(possible_services)


class MergedServiceLoader(Loader):
    """A class to merge the services from a custom service loader with those of Boto3."""

    def __init__(self) -> None:
        self.custom_service_loader = CustomServiceLoader()
        botocore_session = botocore.session.get_session()
        self.botocore_loader = botocore_session.get_component("data_loader")
        boto3_data_path = os.path.join(os.path.dirname(boto3.__file__), "data")
        self.botocore_loader.search_paths.append(boto3_data_path)

    def list_available_services(self, type_name: str = "resources-1") -> List[str]:
        _ = type_name
        """Return a list of service names that can be loaded."""
        return list(set(self.cloudwanderer_available_services + self.boto3_available_services))

    def determine_latest_version(self, service_name: str, type_name: str) -> str:
        return max(self.list_api_versions(service_name, type_name))

    @property
    def cloudwanderer_available_services(self) -> List[str]:
        """Return a list of services defined by CloudWanderer."""
        return self.custom_service_loader.available_services

    @property
    def boto3_available_services(self) -> List[str]:
        """Return a list of services defined by Boto3."""
        return self.botocore_loader.list_available_services(type_name="resources-1")

    def list_api_versions(self, service_name: str, type_name: str) -> List[str]:
        logger.debug("list_api_version, service_name: %s, type_name: %s", service_name, type_name)
        try:
            boto3_api_versions = self.botocore_loader.list_api_versions(service_name=service_name, type_name=type_name)
        except DataNotFoundError:
            boto3_api_versions = []
        try:
            custom_api_versions = self.custom_service_loader.list_api_versions(
                service_name=service_name, type_name=type_name
            )
        except UnsupportedServiceError:
            custom_api_versions = []

        if not boto3_api_versions and not custom_api_versions:
            raise UnsupportedServiceError(
                f"{service_name} is not supported by either Boto3 or CloudWanderer's "
                f"custom services for {type_name}.json"
            )

        if custom_api_versions:
            return custom_api_versions

        return boto3_api_versions

    @memoized_method()
    def load_service_model(self, service_name: str, type_name: str, api_version: Optional[str] = None) -> OrderedDict:
        logger.debug(
            "botocore_loaders load_service_model service_name %s, type_name %s, api_version %s",
            service_name,
            type_name,
            api_version,
        )
        if not api_version:
            api_version = self.determine_latest_version(service_name=service_name, type_name=type_name)
        try:
            boto3_definition = self.botocore_loader.load_service_model(
                service_name, type_name=type_name, api_version=api_version
            )
        except UnknownServiceError:
            boto3_definition = OrderedDict()

        custom_service_definition = self._get_custom_service_definition(
            service_name, type_name=type_name, api_version=api_version
        )

        if not boto3_definition and not custom_service_definition:
            raise UnsupportedServiceError(
                f"{service_name} is not supported by either Boto3 or CloudWanderer's custom "
                f"services for api_version {api_version}, type {type_name}"
            )
        merged_dict = OrderedDict(
            {
                "service": OrderedDict(
                    {
                        **custom_service_definition.get("service", {}),
                        **{
                            "hasMany": OrderedDict(
                                {
                                    **(jmespath.search("service.hasMany", boto3_definition) or OrderedDict({})),
                                    **(
                                        jmespath.search("service.hasMany", custom_service_definition) or OrderedDict({})
                                    ),
                                }
                            )
                        },
                    }
                ),
                "resources": OrderedDict(
                    {
                        **boto3_definition.get("resources", OrderedDict({})),
                        **custom_service_definition.get("resources", OrderedDict({})),
                    }
                ),
            }
        )
        # logger.warning(merged_dict['resources'].get('RouteTable'))
        return merged_dict

    def _get_custom_service_definition(self, service_name: str, type_name: str, api_version: str) -> dict:
        """Get the custom CloudWanderer definition for service_name so we can merge it with Boto3's.

        Arguments:
            service_name: The PascalCase name of the service to get the definition of.
            api_version: The version of the api to get the definition of.
            type_name: The type of definition to get.
        """
        if not api_version:
            api_version = self.determine_latest_version(service_name=service_name, type_name=type_name)
        try:
            return self.custom_service_loader.get_service_definition(
                service_name=service_name, type_name=type_name, api_version=api_version
            )
        except UnsupportedServiceError:
            return {}


# # TODO: Normalising servicemapping as servicemap


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
        region_request:
            An optional definition for how to perform a secondary query to
            discover the region in which this resource exists.
        parent_resource_type:
            The snake_case resource type of the parent (if this is a subresource).
        ignored_subresources:
            A list of snake case subresources which exist in the Boto3 definition but should be ignored.
        default_filters:
            A dict of arguments to supply to the API Method used when enumerating this resource type.
            This can be overridden by the user with the ``filters`` argument.
        service_map:
            A link back to the parent :class:`ServiceMap` object.
        requires_load_for_full_metadata:
            If set ``resource.load()`` is called when fetching a list of these resources.
            Resources in a big increase in the number of API calls as one must be made for *each* resource.
        regional_resource:
            Whether or not this resource exists in every region.
    """

    type: Optional[str]
    region_request: Optional["ResourceRegionRequest"]
    ignored_subresources: list
    default_filters: Dict[str, Any]
    service_map: ServiceMap
    relationships: List["RelationshipSpecification"]
    secondary_attribute_maps: List["SecondaryAttributeMap"]
    requires_load_for_full_metadata: bool = False
    regional_resource: bool = True

    @classmethod
    def factory(
        cls,
        service_map: ServiceMap,
        definition: Dict[str, Any],
    ) -> "ResourceMap":
        return cls(
            type=definition.get("type"),
            region_request=ResourceRegionRequest.factory(definition.get("regionRequest")),
            ignored_subresources=definition.get("ignoredSubresources", []),
            requires_load_for_full_metadata=definition.get("requiresLoadForFullMetadata", False),
            regional_resource=definition.get("regionalResource", True),
            default_filters=definition.get("defaultFilters", {}),
            service_map=service_map,
            relationships=[
                RelationshipSpecification.factory(relationship_specification)
                for relationship_specification in definition.get("relationships", [])
            ],
            secondary_attribute_maps=[
                SecondaryAttributeMap(source_path=mapping["sourcePath"], destination_name=mapping["destinationName"])
                for mapping in definition.get("secondaryAttributeMaps", [])
            ],
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
