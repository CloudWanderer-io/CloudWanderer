"""Boto3 Loaders.

Loaders and data classes to load custom CloudWanderer Boto3 service definitions and merge them with the boto3
provided ones. This allows cloudwanderer to extend Boto3 to support AWS resources that it does not support natively.
We can do this quite easily because CloudWanderer only needs a fraction of the functionality that native
Boto3 resources provide (i.e. the description of the resources).
"""
from genericpath import isfile
from ..urn import PartialUrn
import logging
import os
import pathlib
from functools import lru_cache
from typing import Any, Dict, Generator, List, NamedTuple, Optional, OrderedDict, Tuple

import boto3
import botocore  # type: ignore
import jmespath  # type: ignore
from boto3.resources.base import ServiceResource
from boto3.resources.model import Collection, ResourceModel
from botocore.exceptions import UnknownServiceError, DataNotFoundError  # type: ignore

from ..cache_helpers import cached_property, memoized_method
from ..exceptions import UnsupportedServiceError
from ..utils import snake_to_pascal
from pathlib import Path
import json

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


class MergedServiceLoader:
    """A class to merge the services from a custom service loader with those of Boto3."""

    @lru_cache()  # type: ignore
    def __init__(self) -> None:
        self.custom_service_loader = CustomServiceLoader()
        botocore_session = botocore.session.get_session()
        self.boto3_loader = botocore_session.get_component("data_loader")
        self.boto3_loader.search_paths.append(os.path.join(os.path.dirname(boto3.__file__), "data"))

        # This does not need to honour the user's session because it is *only* used to list resources
        self.non_specific_boto3_session = boto3.session.Session()

    def list_available_services(self) -> List[str]:
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
        return self.non_specific_boto3_session.get_available_resources()

    def list_api_versions(self, service_name: str, type_name: str) -> List[str]:
        try:
            boto3_api_versions = self.boto3_loader.list_api_versions(service_name=service_name, type_name=type_name)
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
                f"{service_name} is not supported by either Boto3 or CloudWanderer's custom services"
            )

        if custom_api_versions:
            return custom_api_versions

        return boto3_api_versions

    @memoized_method()
    def load_service_model(self, service_name: str, type_name: str, api_version: str) -> OrderedDict:
        try:
            boto3_definition = self.boto3_loader.load_service_model(
                service_name, type_name=type_name, api_version=api_version
            )
        except UnknownServiceError:
            boto3_definition = OrderedDict()

        custom_service_definition = self._get_custom_service_definition(
            service_name, type_name=type_name, api_version=api_version
        )

        if not boto3_definition and not custom_service_definition:
            raise UnsupportedServiceError(
                f"{service_name} is not supported by either Boto3 or CloudWanderer's custom services"
            )

        return OrderedDict(
            {
                "service": OrderedDict(
                    {
                        "hasMany": OrderedDict(
                            {
                                **(jmespath.search("service.hasMany", boto3_definition) or OrderedDict({})),
                                **(jmespath.search("service.hasMany", custom_service_definition) or OrderedDict({})),
                            }
                        )
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

    def _get_custom_service_definition(self, service_name: str, type_name: str, api_version: str) -> dict:
        """Get the custom CloudWanderer definition for service_name so we can merge it with Boto3's.

        Arguments:
            service_name: The PascalCase name of the service to get the definition of.
        """
        try:
            return self.custom_service_loader.get_service_definition(
                service_name=service_name, type_name=type_name, api_version=api_version
            )
        except UnsupportedServiceError:
            return {}


# TODO: Normalising servicemapping as servicemap
class ServiceMappingLoader:
    """A class to load and retrieve service mappings.

    Service Mappings provide additional metadata about an AWS service.
    This includes things like, whether it is a global service, whether it has regional resources, etc.
    """

    @lru_cache()  # type: ignore
    def __init__(self) -> None:
        """Load and retrieve service mappings."""
        self.service_mappings_path = os.path.join(pathlib.Path(__file__).parent.absolute(), "service_mappings")

    def get_service_mapping(self, service_name: str) -> "ServiceMap":
        """Return the mapping for service_name.

        Arguments:
            service_name (str): The name of the service (e.g. ``'ec2'``)
        """
        return ServiceMap.factory(name=service_name, definition=self.service_maps.get(service_name, {}))

    @cached_property
    def service_maps(self) -> Dict[str, Any]:
        """Return our custom resource definitions."""
        return load_json_definitions(self.service_mappings_path)


class ServiceMap(NamedTuple):
    """Specification for additional CloudWanderer specific metadata about a Boto3 service."""

    name: str
    resource_definition: dict
    global_service: bool
    global_service_region: str
    service_definition: dict
    boto3_definition: dict

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
            boto3_resource_name: The (snake_case) name of the resource map to get.
        """
        boto3_resource_name = snake_to_pascal(resource_type)
        return ResourceMap.factory(
            service_map=self,
            definition=self.resource_definition.get(boto3_resource_name, {}),
            boto3_resource_model=ResourceModel(
                name=boto3_resource_name,
                definition=self.boto3_definition["resources"].get(boto3_resource_name, {}),
                resource_defs=self.boto3_definition["resources"],
            ),
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
            boto3_definition=MergedServiceLoader().get_service_definition(service_name=name),
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
        boto3_resource_model:
            The Boto3 model for this resource.
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
    resource_type: str
    parent_resource_type: str
    ignored_subresources: list
    boto3_resource_model: ResourceModel
    default_filters: Dict[str, Any]
    service_map: ServiceMap
    requires_load_for_full_metadata: bool = False
    regional_resource: bool = True

    @classmethod
    def factory(
        cls,
        service_map: ServiceMap,
        definition: Dict[str, Any],
        boto3_resource_model: ResourceModel,
    ) -> "ResourceMap":
        return cls(
            type=definition.get("type"),
            region_request=ResourceRegionRequest.factory(definition.get("regionRequest")),
            ignored_subresources=definition.get("ignoredSubresources", []),
            resource_type=botocore.xform_name(boto3_resource_model.name),
            parent_resource_type=definition.get("parentResourceType", ""),
            requires_load_for_full_metadata=definition.get("requiresLoadForFullMetadata", False),
            regional_resource=definition.get("regionalResource", True),
            default_filters=definition.get("defaultFilters", {}),
            service_map=service_map,
            boto3_resource_model=boto3_resource_model,
        )

    def should_query_resources_in_region(self, region: str) -> bool:
        """Return whether this resource should be queried from this region.

        Arguments:
            region: The region in which to query the resource.
        """
        if not self.service_map.is_global_service:
            return True
        return self.service_map.is_global_service and self.service_map.global_service_region == region

    @property
    def dependent_resource_types(self) -> List[str]:
        """Return a list of CloudWanderer style dependent resource types it's possible for this resource type to have."""
        types = []
        for dependent_resource_model in self._dependent_resource_models:
            if not dependent_resource_model.resource:
                continue
            types.append(botocore.xform_name(dependent_resource_model.resource.model.name))
        return types

    # @property
    # def subresource_models(self) -> Generator[Collection, None, None]:
    #     """Yield the Boto3 models for the CloudWanderer style subresources of this resource type."""
    #     models = {}
    #     for collection_resource_map, collection_model in self._boto3_collection_models:
    #         response_resource = collection_model.resource
    #         if not response_resource or not self._is_collection_model_a_subresource(
    #             collection_resource_map, response_resource.model
    #         ):
    #             continue

    #         collection_resource_name = botocore.xform_name(response_resource.model.name)
    #         models[collection_resource_name] = collection_model
    #     yield from models.values()

    # def _is_collection_model_a_subresource(
    #     self, collection_resource_map: "ResourceMap", resource_model: ResourceModel
    # ) -> bool:

    #     if collection_resource_map.type in ["secondaryAttribute", "baseResource"] or resource_model is None:
    #         return False
    #     collection_resource_name = botocore.xform_name(resource_model.name)

    #     if len(resource_model.identifiers) == 1 and collection_resource_map.type != "subresource":
    #         return False
    #     if resource_model.name in self.ignored_subresource_types:
    #         logger.debug(
    #             "% is defined as an ignored subresource type by the %s servicemap",
    #             collection_resource_name,
    #             self.service_map.name,
    #         )
    #         return False

    #     return True

    # @property
    # def _boto3_collection_models(self) -> Generator[Tuple["ResourceMap", Collection], None, None]:
    #     """Yield the ResourceMaps and Collections for this resource type.

    #     This is used exclusively for subresources because subresources have a 1:many relationship with
    #     their parent resource.
    #     """
    #     for boto3_collection in self.boto3_resource_model.collections:
    #         if boto3_collection.resource is None:
    #             continue
    #         collection_resource_map = self.service_map.get_resource_map(boto3_collection.resource.model.name)
    #         yield collection_resource_map, boto3_collection

    @property
    def ignored_subresource_types(self) -> List:
        """Return a list of (PascalCase) ignored subresource types."""
        return [ignored_subresource["type"] for ignored_subresource in self.ignored_subresources]


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
