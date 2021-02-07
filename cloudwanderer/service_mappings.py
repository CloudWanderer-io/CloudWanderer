"""Provides a way to map resources back to the regions they reside in as well as expose other metadata.

In some cases we need to perform additional API calls to discover the region in which a resource resides.
The most well-known example of this is s3 buckets which require an additional API call to get their region.
When a resource is passed in that doesn't have a Global Service Mapping,
the :class:`~boto3.session.Session`'s region is used.

Additionally this is used to expose information about whether custom resources
should be stored as secondary attributes or resources.
"""
import json
import os
import pathlib
from typing import Any, Iterator, List

import boto3
import jmespath
from boto3.resources.model import ResourceModel
from botocore.client import ClientCreator

from .custom_resource_definitions import _get_resource_definitions


class ServiceMappingCollection:
    """Load and retrieve service mappings.

    Arguments:
        boto3_session (boto3.session.Session): The :class:`boto3.session.Session` object to use for any queries.
    """

    def __init__(self, boto3_session: boto3.session.Session = None) -> str:
        """Load and retrieve service mappings.

        Arguments:
            boto3_session (boto3.session.Session):
                The boto3 session to use to query additional resource information like region.

        """
        self.boto3_session = boto3_session or boto3.Session()
        self.service_mappings_path = os.path.join(
            pathlib.Path(__file__).parent.absolute(),
            'service_mappings'
        )
        self._service_maps = None

    def get_service_mapping(self, service_name: str) -> List['ServiceMapping']:
        """Return the mapping for service_name.

        Arguments:
            service_name (str): The name of the service (e.g. ``'ec2'``)
        """
        if self._service_maps is None:
            self._service_maps = self.get_service_maps()

        return self._service_maps.get(service_name, ServiceMapping(
            service_name=service_name,
            service_mapping={},
            boto3_session=self.boto3_session,
        ))

    def get_service_maps(self) -> List['ServiceMapping']:
        """Return our custom resource definitions."""
        service_mappings = {}
        for service_name in self._list_service_mappings():
            service_mapping = self._load_service_mapping(service_name)
            service_mappings[service_name] = ServiceMapping(
                service_name=service_name,
                service_mapping=service_mapping,
                boto3_session=self.boto3_session
            )
        return service_mappings

    def resource_regions_returned_from_api_region(
            self, service_name: str, region_name: str, enabled_regions: List[str]) -> Iterator[str]:
        """Return a list of regions which will be discovered for this resource type in this region.

        Usually this will just return the region which is passed in, but some resources are only queryable
        from a single region despite having resources from multiple regions (e.g. s3 buckets)

        Arguments:
            service_name (str):
                The name of the service to check (e.g. ``'ec2'``)
            region_name (str):
                The name of the region to check (e.g. ``'eu-west-1'``)
            enabled_regions (List[str]):
                The full list of regions enabled in this account. This is returned if the service has a global
                API but regional resources (e.g. S3 Buckets)
        """
        service_map = self.get_service_mapping(service_name=service_name)
        if not service_map.is_global_service:
            yield region_name
            return

        if service_map.global_service_region != region_name:
            return
        elif not service_map.has_regional_resources:
            yield region_name
        else:
            yield from enabled_regions

    def _load_service_mapping(self, service_name: str) -> dict:
        with open(os.path.join(self.service_mappings_path, f"{service_name}.json")) as definition_path:
            return json.load(definition_path)

    def _list_service_mappings(self) -> List[str]:
        return [
            file_name.replace('.json', '')
            for file_name in os.listdir(self.service_mappings_path)
            if os.path.isfile(os.path.join(self.service_mappings_path, file_name))
        ]


class ServiceMapping:
    """Expose additional metadata about services and resources that isn't supported in boto3's model."""

    def __init__(
            self, service_name: str, service_mapping: dict, boto3_session: boto3.session.Session = None) -> None:
        """Instantiate the ServiceMapping.

        Arguments:
            service_name (str):
                The name of the service mapping to instantiate.
            service_mapping (dict):
                The service mapping to instantiate.
            boto3_session (boto3.session.Session):
                The :class:`~boto3.session.Session`
                to use to query for resource region information.
        """
        self.boto3_session = boto3_session or boto3.Session()
        self.service_name = service_name
        self.service_mapping = service_mapping
        self.boto3_client = self.boto3_session.client(service_name)
        self.boto3_service_definition = _get_resource_definitions().definitions[service_name]

    @property
    def global_service_region(self) -> bool:
        """Return the primary region for this global service (if it not one, return None)."""
        return self._service_details.get('globalServiceRegion')

    @property
    def has_regional_resources(self) -> bool:
        """Return ``True`` if this service has resources in regions other than the primary service region.

        Also returns True if there is no service_mapping (i.e. this is not a known service).

        Raises:
            AttributeError: Occurs if the service does not have a regionalResources key in its definition.
        """
        if self.service_mapping == {}:
            return True
        try:
            return self._service_details['regionalResources']
        except KeyError:
            raise AttributeError(f"{self.__class__.__name__} {self.service_name} does not have a regionalResources key")

    @property
    def _service_details(self) -> dict:
        """Return the dictionary specifying details about the service."""
        return self.service_mapping.get('service', {})

    @property
    def is_global_service(self) -> bool:
        """Return whether this mapping is for a global service.

        Raises:
            AttributeError: Occurs if the service does not have globalService key in its definition.
        """
        if self._service_details == {}:
            return False
        try:
            return self._service_details['globalService']
        except KeyError:
            raise AttributeError(
                f"{self.__class__.__name__} {self.service_name} does not have a value for globalService")

    def get_resource_region(self, resource: boto3.resources.model.ResourceModel, default_region: str) -> str:
        """Get the region of a :class:`boto3.resources.model.ResourceModel` object.

        Arguments:
            resource (boto3.resources.model.ResourceModel):
                The :class:`~boto3.resources.model.ResourceModel` to find the region of.
            default_region (str):
                The region to return if there is no gloabl service mapping for this resource type.
        """
        if self.service_mapping == {}:
            return default_region
        if self.has_regional_resources and not self.is_global_service:
            return default_region
        if not self.has_regional_resources and self.is_global_service:
            return self.service_mapping.get('service', {}).get('globalServiceRegion')
        try:
            resource_mapping = self.get_resource_mapping(resource.meta.resource_model.name)
        except GlobalServiceResourceMappingNotFound:
            return self.service_mapping.get('service', {}).get('globalServiceRegion')
        return resource_mapping.get_region(resource)

    @property
    def resources(self) -> List[str]:
        """Return a list of resources we have mappings for."""
        return [resource.lower() for resource in self.service_mapping.get('resources', {}).keys()]

    def get_resource_mapping(self, resource_type: str) -> ResourceModel:
        """Get the resource mapping for resource_type.

        Arguments:
            resource_type (str): The resource type in PascalCase (e.g. ``'Vpc'``).

        Raises:
            GlobalServiceResourceMappingNotFound: Occurs if theres no global resource mapping for this service.
        """
        resource_name = self._lookup_resource_name(resource_type)
        if resource_name is None:
            raise GlobalServiceResourceMappingNotFound(
                f"Global resource mapping not found for {self.service_name} {resource_type}")
        return CloudWandererResourceMapping(
            service_mapping=self,
            name=resource_name,
            mapping=self.service_mapping['resources'][resource_name],
            resource_definition=self.boto3_service_definition['resources'][resource_name],
            boto3_client=self.boto3_client)

    def _lookup_resource_name(self, resource_name: str) -> str:
        """Return a PascalCase resource name from the resources mapping given a lowercase resource name.

        Arguments:
            resource_name (str): the lowercase resource name to lookup
        """
        resource_names = [(key, key.lower()) for key in self.service_mapping.get('resources', {})]
        return next(iter(
            resource_tuple[0] for resource_tuple in resource_names if resource_tuple[1] == resource_name.lower()
        ), None)


class CloudWandererResourceMapping:
    """CloudWanderer specific information about a boto3 resource."""

    def __init__(
            self, service_mapping: ServiceMapping, name: str, mapping: dict, resource_definition: dict,
            boto3_client: ClientCreator) -> None:
        """Initialise the CloudWandererResourceMapping.

        Arguments:
            service_mapping (ServiceMapping): The :class:`ServiceMapping` for this resource.
            name (str): The name of the resource
            mapping (dict): The resource's cloudwanderer mapping data
            resource_definition (dict): The boto3 resource definition
            boto3_client: The boto3 client for this resource
        """
        self.service_mapping = service_mapping
        self.name = name
        self._mapping = mapping
        self.boto3_client = boto3_client
        self.resource_definition = resource_definition

    @property
    def resource_type(self) -> str:
        """Return the resource type (e.g. Resource, SecondaryAttribute).

        Raises:
            AttributeError: Occurs if this resource's mapping does not have a type.
        """
        try:
            return self._mapping['type']
        except KeyError:
            raise AttributeError(f"{self.__class__.__name__} - {self.name} does not have a type")

    def get_region(self, resource: boto3.resources.model.ResourceModel) -> str:
        """Return the resource passed in.

        Arguments:
            resource (boto3.resources.model.ResourceModel): The :class:`~boto3.resources.model.ResourceModel`
                to get the region for
        """
        method = getattr(self.boto3_client, self._request_mapping['operation'])
        result = method(**self._build_params(resource))
        return jmespath.search(
            self._request_mapping['pathToRegion'], result) or self._request_mapping.get('defaultValue', None)

    @property
    def secondary_attributes(self) -> List[str]:
        """Return a list of secondary attributes for this resource."""
        for subresource_name in self.resource_definition.get('has', []):
            try:
                resource_mapping = self.service_mapping.get_resource_mapping(subresource_name)
            except GlobalServiceResourceMappingNotFound:
                continue
            if resource_mapping.resource_type == 'secondaryAttribute':
                yield subresource_name

    @property
    def has_secondary_attributes(self) -> bool:
        """Return True if this resource has secondary attributes."""
        return bool(next(self.secondary_attributes, None))

    @property
    def _request_mapping(self) -> dict:
        try:
            return self._mapping['regionRequest']
        except KeyError:
            raise AttributeError(f"{self.__class__.__name__} - {self.name} does not have a regionRequest")

    def _build_params(self, resource: ResourceModel) -> dict:
        params = {}
        for param_mapping in self._mapping['regionRequest']['params']:
            key = param_mapping['target']
            params[key] = self._get_param_value(resource, param_mapping)
        return params

    def _get_param_value(self, resource: ResourceModel, param_mapping: dict) -> Any:
        if param_mapping['source'] == 'resourceAttribute':
            return getattr(resource, param_mapping['name'])
        raise AttributeError(f"Invalid param source {param_mapping['source']}")


class GlobalServiceResourceMappingNotFound(Exception):
    """Global Service Resource Mapping not Found."""
