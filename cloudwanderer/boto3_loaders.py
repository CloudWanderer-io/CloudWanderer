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
from functools import lru_cache
from typing import Any, List, NamedTuple, Union

import boto3
import botocore
from boto3.resources.base import ServiceResource
from botocore.exceptions import UnknownServiceError

from .exceptions import UnsupportedServiceError

logger = logging.getLogger(__file__)


def load_json_definitions(path: str) -> List[Union[list, dict]]:
    """Return the parsed contents of all JSON files in a given path.

    Arguments:
        path: The path to load JSON files from.
    """
    definition_files = [
        (os.path.abspath(os.path.join(path, file_name)), file_name.rstrip(".json"))
        for file_name in os.listdir(path)
        if os.path.isfile(os.path.join(path, file_name))
    ]
    definitions = {}
    for file_path, service_name in definition_files:
        with open(file_path) as definition_path:
            definitions[service_name] = json.load(definition_path)
    return definitions


class CustomServiceLoader:
    """A class to load custom services."""

    def __init__(self, definition_path: str = "resource_definitions") -> None:
        self.service_definitions_path = os.path.join(pathlib.Path(__file__).parent.absolute(), definition_path)

    @property
    @lru_cache()
    def service_definitions(self) -> dict:
        """Return our custom resource definitions."""
        return load_json_definitions(self.service_definitions_path)

    @lru_cache()
    def get_service_definition(self, service_name: str) -> dict:
        try:
            return self.service_definitions[service_name]
        except KeyError:
            raise UnsupportedServiceError(f"{service_name} does not exist as a custom CloudWanderer service.")

    @property
    @lru_cache()
    def available_services(self) -> List[str]:
        """Return a list of available snake_case service names."""
        return list(self.service_definitions.keys())


class MergedServiceLoader:
    """A class to merge the services from a custom service loader with those of Boto3."""

    def __init__(self, custom_service_loader: CustomServiceLoader = None) -> None:
        self._custom_service_loader = custom_service_loader or CustomServiceLoader()
        botocore_session = botocore.session.get_session()
        self._boto3_loader = botocore_session.get_component("data_loader")
        self._boto3_loader.search_paths.append(os.path.join(os.path.dirname(boto3.__file__), "data"))

        # This does not need to honour the user's session because it is *only* used to list resources
        self.non_specific_boto3_session = boto3.Session()

    @property
    @lru_cache()
    def available_services(self) -> List[str]:
        """Return a list of service names that can be loaded by :class:`Boto3Services.get_service`."""
        return list(
            set(
                self._custom_service_loader.available_services
                + self.non_specific_boto3_session.get_available_resources()
            )
        )

    @lru_cache()
    def get_service_definition(self, service_name: str) -> dict:
        """Return a combined dictionary service definition of both CloudWanderer and Boto3 services.

        Arguments:
            service_name: The PascalCase name of the service to return the definition for.

        Raises:
            UnsupportedServiceError: Occurs if a service is requested that CloudWanderer does not support.
        """
        boto3_definition = self._get_boto3_definition(service_name)
        custom_service_definition = self._get_custom_service_definition(service_name)

        if not boto3_definition and not custom_service_definition:
            raise UnsupportedServiceError(
                f"{service_name} is not supported by either Boto3 or CloudWanderer's custom services"
            )

        return {
            "service": {**boto3_definition.get("service", {}), **custom_service_definition.get("service", {})},
            "resources": {**boto3_definition.get("resources", {}), **custom_service_definition.get("resources", {})},
        }

    def _get_custom_service_definition(self, service_name: str) -> dict:
        """Get the custom cloudwanderer definition for service_name so we can merge it with Boto3's.

        Arguments:
            service_name: The PascalCase name of the service to get the definition of.
        """
        try:
            return self._custom_service_loader.get_service_definition(service_name=service_name)
        except UnsupportedServiceError:
            return {}

    def _get_boto3_definition(self, service_name: str) -> dict:
        """Get the boto3 definition for service_name so we can merge it with CloudWanderer's.

        Arguments:
            service_name (str): The name of the service (e.g. ``'ec2'``)
        """
        try:
            return self._boto3_loader.load_service_model(service_name, "resources-1", None)
        except UnknownServiceError:
            return {}


class ServiceMappingLoader:
    """A class to load and retrieve service mappings.

    Service Mappings provide additional metadata about an AWS service.
    This includes things like, whether it is a global service, whether it has regional resources, etc.
    """

    def __init__(self) -> str:
        """Load and retrieve service mappings."""
        self.service_mappings_path = os.path.join(pathlib.Path(__file__).parent.absolute(), "service_mappings")

    def get_service_mapping(self, service_name: str) -> dict:
        """Return the mapping for service_name.

        Arguments:
            service_name (str): The name of the service (e.g. ``'ec2'``)
        """
        return self.service_maps.get(service_name, {})

    @property
    @lru_cache()
    def service_maps(self) -> List[dict]:
        """Return our custom resource definitions."""
        return load_json_definitions(self.service_mappings_path)


class ServiceMap(NamedTuple):
    """Specification for additional CloudWanderer specific metadata about a Boto3 service."""

    name: str
    resource_definition: dict
    global_service: bool
    global_service_region: str
    regional_resources: bool
    service_definition: dict

    @property
    def is_global_service(self) -> bool:
        """Return whether this service is a global service."""
        return self.global_service

    @property
    def is_default_service(self) -> bool:
        """Return True if this service has no definition and should return default values."""
        return self.service_definition == {}

    def get_resource_map(self, boto3_resource_name: str) -> "ResourceMap":
        """Return the resource map given a PascalCase resource name.

        Arguments:
            boto3_resource_name: The (PascalCase) name of the resource map to get.
        """
        return ResourceMap.factory(self.resource_definition.get(boto3_resource_name, {}))

    @classmethod
    def factory(cls, name: str, definition: dict) -> "ServiceMap":
        service_definition = definition.get("service", {})
        return cls(
            name=name,
            global_service=service_definition.get("globalService", False),
            regional_resources=service_definition.get("regionalResources", True),
            global_service_region=service_definition.get("globalServiceRegion"),
            service_definition=service_definition,
            resource_definition=definition.get("resources", {}),
        )


class ResourceMap(NamedTuple):
    """Specification for additional CloudWanderer specific metadata about a Boto3 resource type."""

    type: str
    region_request: dict

    @classmethod
    def factory(cls, definition: dict) -> "ResourceMap":
        return cls(
            type=definition.get("type"),
            region_request=ResourceRegionRequest.factory(definition.get("regionRequest")),
        )


class ResourceRegionRequest(NamedTuple):
    """Specification for a request to get a resource's region."""

    operation: str
    params: list
    path_to_region: str
    default_value: str

    @classmethod
    def factory(cls, definition: dict) -> "ResourceRegionRequest":
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
