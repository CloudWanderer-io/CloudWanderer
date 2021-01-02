"""Provides a way to map resources back to the regions they reside in as well as expose other metadata.

In some cases we need to perform additional API calls to discover the region in which a resource resides.
The most well-known example of this is s3 buckets which require an additional API call to get their region.
When a resource is passed in that doesn't have a Global Service Mapping,
the :class:`~boto3.session.Session`'s region is used.

Additionally this is used to expose information about whether custom resources
should be stored as secondary attributes or resources.
"""
from typing import Any, List
import os
import pathlib
import json
import boto3
from botocore.client import ClientCreator
import jmespath
from boto3.resources.model import ResourceModel


class ServiceMappingCollection:
    """Load and retrieve service mappings.

    Arguments:
        boto3_session (boto3.session.Session): The :class:`boto3.session.Session` object to use for any queries.
    """

    def __init__(self, boto3_session: boto3.session.Session = None) -> str:
        """Load and retrieve service mappings."""
        self.boto3_session = boto3_session or boto3.Session()
        self.service_mappings_path = os.path.join(
            pathlib.Path(__file__).parent.absolute(),
            'service_mappings'
        )
        self._service_maps = None

    def get_service_mapping(self, service_name: str) -> List['ServiceMapping']:
        """Returns the mapping for service_name."""
        if self._service_maps is None:
            self._service_maps = self.get_service_maps()
        default_service_map = ServiceMapping(
            service_name=service_name,
            service_mapping={},
            boto3_session=self.boto3_session
        )
        return self._service_maps.get(service_name, default_service_map)

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
    """Expose additional metadata about services and resources that isn't supported in boto3's model.

    Arguments:
        service_name (str): The name of the service mapping to instantiate.
        service_mapping (dict): The service mapping to instantiate.
        boto3_session (boto3.session.Session): The :class:`~boto3.session.Session`
            to use to query for resource region information.
    """

    def __init__(self, service_name: str, service_mapping: dict, boto3_session: boto3.session.Session = None) -> None:
        """Instantiate the ServiceMapping."""
        self.boto3_session = boto3_session or boto3.Session()
        self.service_name = service_name
        self.service_mapping = service_mapping
        self.boto3_client = self.boto3_session.client(service_name)

    def has_global_resources_in_region(self, region: str) -> bool:
        """Return ``True`` if service has **only** resources and their primary endpoint is this region."""
        if not self.is_global_service:
            return False
        if self.has_regional_resources:
            return False
        return self._service_details.get('region') == region

    @property
    def has_regional_resources(self) -> bool:
        """Returns ``True`` if this service has resources in regions other than the primary service region.

        Also returns True if there is no service_mapping (i.e. this is not a known service).
        """
        if self.service_mapping is None:
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
        """Return whether this mapping is for a global service."""
        try:
            return self._service_details['globalService']
        except KeyError:
            raise AttributeError(
                f"{self.__class__.__name__} {self.service_name} does not have a value for globalService")

    def get_resource_region(self, resource: ResourceModel, default_region: str) -> str:
        """Get the region of a :class:`boto3.resources.base.ServiceResource` object.

        Arguments:
            resource (boto3.resources.base.ServiceResource): The :class:`~boto3.resources.base.ServiceResource`
                to find the region of.
            default_region (str): The region to return if there is no gloabl service mapping for this resource type.
        """
        if self.service_mapping is None:
            return default_region
        if self.has_regional_resources and not self.is_global_service:
            return default_region
        if not self.has_regional_resources and self.is_global_service:
            return self.service_mapping.get('service', {}).get('region')
        try:
            resource_mapping = self.get_resource_mapping(resource.meta.resource_model.name)
        except GlobalServiceResourceMappingNotFound:
            return self.service_mapping.get('service', {}).get('region')
        return resource_mapping.get_region(resource)

    def get_resource_mapping(self, resource_type: str) -> ResourceModel:
        """Get the resource mapping for resource_type.

        Arguments:
            resource_type (str): The resource type in PascalCase (e.g. ``'Vpc'``).
        """
        if resource_type not in self.service_mapping.get('resources', []):
            raise GlobalServiceResourceMappingNotFound(
                f"Global resource mapping not found for {self.service_name} {resource_type}")
        return CloudWandererResourceMapping(
            resource_type, self.service_mapping['resources'][resource_type], self.boto3_client)


class CloudWandererResourceMapping:
    """CloudWanderer specific information about a boto3 resource.

    Arguments:
        name (str): The name of the resource
        mapping (dict): The resource's cloudwanderer mapping data
        boto3_client: The boto3 client for this resource
    """

    def __init__(self, name: str, mapping: dict, boto3_client: ClientCreator) -> None:
        """Initialise the CloudWandererResourceMapping."""
        self.name = name
        self._mapping = mapping
        self.boto3_client = boto3_client

    @property
    def resource_type(self) -> str:
        """The resource type (e.g. Resource, SecondaryAttribute)."""
        try:
            return self._mapping['type']
        except KeyError:
            raise AttributeError(f"{self.__class__.__name__} - {self.name} does not have a type")

    def get_region(self, resource: ResourceModel) -> str:
        """Return the resource passed in.

        Arguments:
            resource (boto3.resources.model.ResourceModel): The :class:`boto3.resources.model.ResourceModel`
                to get the region for
        """
        method = getattr(self.boto3_client, self._request_mapping['operation'])
        result = method(**self._build_params(resource))
        return jmespath.search(
            self._request_mapping['pathToRegion'], result) or self._request_mapping.get('defaultValue', None)

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
    pass
