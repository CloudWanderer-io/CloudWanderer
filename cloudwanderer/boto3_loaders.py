"""Boto3 Loaders.

Loaders and data classes to load custom CloudWanderer Boto3 service definitions and merge them with the boto3
provided ones. This allows cloudwanderer to extend Boto3 to support AWS resources that it does not support natively.
We can do this quite easily because CloudWanderer only needs a fraction of the functionality that native
Boto3 resources provide (i.e. the description of the resources).
"""
import logging
import os
import pathlib
from functools import lru_cache
from typing import Any, Dict, Generator, List, NamedTuple, Optional, Tuple

import boto3
import botocore  # type: ignore
import jmespath  # type: ignore
from boto3.resources.base import ServiceResource
from boto3.resources.model import Collection, ResourceModel
from botocore.exceptions import UnknownServiceError  # type: ignore

from .cache_helpers import cached_property, memoized_method
from .exceptions import UnsupportedServiceError
from .models import AWSGetAndCleanUp, CleanupAction, GetAction
from .utils import load_json_definitions

logger = logging.getLogger(__file__)


class CustomServiceLoader:
    """A class to load custom services."""

    def __init__(self, definition_path: str = "resource_definitions") -> None:
        self.service_definitions_path = os.path.join(pathlib.Path(__file__).parent.absolute(), definition_path)

    @cached_property
    def service_definitions(self) -> dict:
        """Return our custom resource definitions."""
        return load_json_definitions(self.service_definitions_path)

    def get_service_definition(self, service_name: str) -> dict:
        try:
            return self.service_definitions[service_name]
        except KeyError:
            raise UnsupportedServiceError(f"{service_name} does not exist as a custom CloudWanderer service.")

    @property
    def available_services(self) -> List[str]:
        """Return a list of available snake_case service names."""
        return list(self.service_definitions.keys())


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

    @property
    def available_services(self) -> List[str]:
        """Return a list of service names that can be loaded."""
        return list(set(self.cloudwanderer_available_services + self.boto3_available_services))

    @property
    def cloudwanderer_available_services(self) -> List[str]:
        """Return a list of services defined by CloudWanderer."""
        return self.custom_service_loader.available_services

    @property
    def boto3_available_services(self) -> List[str]:
        """Return a list of services defined by Boto3."""
        return self.non_specific_boto3_session.get_available_resources()

    @memoized_method()
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
            "service": {
                "hasMany": {
                    **(jmespath.search("service.hasMany", boto3_definition) or {}),
                    **(jmespath.search("service.hasMany", custom_service_definition) or {}),
                }
            },
            "resources": {**boto3_definition.get("resources", {}), **custom_service_definition.get("resources", {})},
        }

    def _get_custom_service_definition(self, service_name: str) -> dict:
        """Get the custom CloudWanderer definition for service_name so we can merge it with Boto3's.

        Arguments:
            service_name: The PascalCase name of the service to get the definition of.
        """
        try:
            return self.custom_service_loader.get_service_definition(service_name=service_name)
        except UnsupportedServiceError:
            return {}

    def _get_boto3_definition(self, service_name: str) -> dict:
        """Get the Boto3 definition for service_name so we can merge it with CloudWanderer's.

        Arguments:
            service_name (str): The name of the service (e.g. ``'ec2'``)
        """
        try:
            return self.boto3_loader.load_service_model(service_name, "resources-1", None)
        except UnknownServiceError:
            return {}


class ServiceMappingLoader:
    """A class to load and retrieve service mappings.

    Service Mappings provide additional metadata about an AWS service.
    This includes things like, whether it is a global service, whether it has regional resources, etc.
    """

    @lru_cache()  # type: ignore
    def __init__(self) -> None:
        """Load and retrieve service mappings."""
        self.service_mappings_path = os.path.join(pathlib.Path(__file__).parent.absolute(), "service_mappings")

    def get_service_mapping(self, service_name: str) -> dict:
        """Return the mapping for service_name.

        Arguments:
            service_name (str): The name of the service (e.g. ``'ec2'``)
        """
        return self.service_maps.get(service_name, {})

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

    def get_resource_map(self, boto3_resource_name: str) -> "ResourceMap":
        """Return the resource map given a PascalCase resource name.

        Arguments:
            boto3_resource_name: The (PascalCase) name of the resource map to get.
        """
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

    def get_and_cleanup_actions(self, query_region: str) -> AWSGetAndCleanUp:
        """Return the query and cleanup actions to be performed if getting this resource type in this region.

        Arguments:
            query_region: The region in which the query would be performed.
        """
        actions = AWSGetAndCleanUp([], [])
        if not self.should_query_resources_in_region(query_region):
            return actions
        if self.service_map.is_global_service and self.regional_resource:
            cleanup_region = "ALL_REGIONS"
        else:
            cleanup_region = query_region
        if self.type != "subresource":
            actions.get_actions.append(
                GetAction(
                    service_name=self.service_map.name,
                    region=query_region,
                    resource_type=self.resource_type,
                )
            )
        actions.cleanup_actions.append(
            CleanupAction(
                service_name=self.service_map.name,
                region=cleanup_region,
                resource_type=self.resource_type,
            )
        )
        return actions

    @property
    def subresource_types(self) -> List[str]:
        """Return a list of CloudWanderer style subresource types it's possible for this resource type to have."""
        types = []
        for subresource_model in self.subresource_models:
            if not subresource_model.resource:
                continue
            types.append(botocore.xform_name(subresource_model.resource.model.name))
        return types

    @property
    def subresource_models(self) -> Generator[Collection, None, None]:
        """Yield the Boto3 models for the CloudWanderer style subresources of this resource type."""
        models = {}
        for collection_resource_map, collection_model in self._boto3_collection_models:
            response_resource = collection_model.resource
            if not response_resource or not self._is_collection_model_a_subresource(
                collection_resource_map, response_resource.model
            ):
                continue

            collection_resource_name = botocore.xform_name(response_resource.model.name)
            models[collection_resource_name] = collection_model
        yield from models.values()

    def _is_collection_model_a_subresource(
        self, collection_resource_map: "ResourceMap", resource_model: ResourceModel
    ) -> bool:

        if collection_resource_map.type in ["secondaryAttribute", "baseResource"] or resource_model is None:
            return False
        collection_resource_name = botocore.xform_name(resource_model.name)

        if len(resource_model.identifiers) == 1 and collection_resource_map.type != "subresource":
            return False
        if resource_model.name in self.ignored_subresource_types:
            logger.debug(
                "% is defined as an ignored subresource type by the %s servicemap",
                collection_resource_name,
                self.service_map.name,
            )
            return False

        return True

    @property
    def _boto3_collection_models(self) -> Generator[Tuple["ResourceMap", Collection], None, None]:
        """Yield the ResourceMaps and Collections for this resource type.

        This is used exclusively for subresources because subresources have a 1:many relationship with
        their parent resource.
        """
        for boto3_collection in self.boto3_resource_model.collections:
            if boto3_collection.resource is None:
                continue
            collection_resource_map = self.service_map.get_resource_map(boto3_collection.resource.model.name)
            yield collection_resource_map, boto3_collection

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
