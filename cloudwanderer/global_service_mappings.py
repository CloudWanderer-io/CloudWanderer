"""Provides a way to map resources back to the regions they reside in.

In some cases we need to perform additional API calls to discover the region in which a resource resides.
The most well-known example of this is s3 buckets which require an additional API call to get their region.
When a resource is passed in that doesn't have a Global Service Mapping,
the :class:`~boto3.session.Session`'s region is used.
"""
from typing import Any, List
import os
import pathlib
import json
import boto3
import botocore
import jmespath
from boto3.resources.model import ResourceModel


class GlobalServiceMappingCollection:
    """Load and retrieve global service mappings.

    Arguments:
        boto3_session (boto3.session.Session): The :class:`boto3.session.Session` object to use for any queries.
    """

    def __init__(self, boto3_session: boto3.session.Session = None) -> str:
        """Load and retrieve global service mappings."""
        self.boto3_session = boto3_session or boto3.Session()
        self.global_service_mappings_path = os.path.join(
            pathlib.Path(__file__).parent.absolute(),
            'global_service_mappings'
        )
        self._global_service_maps = None

    def get_global_service_map(self, service_name: str) -> List['GlobalServiceMapping']:
        """Returns the mapping for service_name."""
        if self._global_service_maps is None:
            self._global_service_maps = self.get_global_service_maps()
        default_service_map = GlobalServiceMapping(
            service_name=service_name,
            service_mapping=None,
            boto3_session=self.boto3_session
        )
        return self._global_service_maps.get(service_name, default_service_map)

    def get_global_service_maps(self) -> List['GlobalServiceMapping']:
        """Return our custom resource definitions."""
        service_mappings = {}
        for service_name in self._list_global_service_mappings():
            service_mapping = self._load_global_service_mapping(service_name)
            service_mappings[service_name] = GlobalServiceMapping(
                service_name=service_name,
                service_mapping=service_mapping,
                boto3_session=self.boto3_session
            )
        return service_mappings

    def _load_global_service_mapping(self, service_name: str) -> dict:
        with open(os.path.join(self.global_service_mappings_path, f"{service_name}.json")) as definition_path:
            return json.load(definition_path)

    def _list_global_service_mappings(self) -> List[str]:
        return [
            file_name.replace('.json', '')
            for file_name in os.listdir(self.global_service_mappings_path)
            if os.path.isfile(os.path.join(self.global_service_mappings_path, file_name))
        ]


class GlobalServiceMapping:
    """Understand the location of global services and their resources.

    Arguments:
        service_name (str): The name of the service mapping to instantiate.
        service_mapping (dict): The service mapping to instantiate.
        boto3_session (boto3.session.Session): The :class:`~boto3.session.Session`
            to use to query for resource region information.
    """

    def __init__(self, service_name: str, service_mapping: dict, boto3_session: boto3.session.Session = None) -> None:
        """Instantiate the GlobalServiceMapping."""
        self.boto3_session = boto3_session or boto3.Session()
        self.service_name = service_name
        self.service_mapping = service_mapping
        self.boto3_client = self.boto3_session.client(service_name)

    def has_global_resources_in_region(self, region: str) -> bool:
        """Return ``True`` if service has **only** global resources and their primary endpoint is this region."""
        if self.has_regional_resources:
            return False
        return self._service_details.get('region') == region

    @property
    def has_regional_resources(self) -> bool:
        """Returns ``True`` if this global service has resources in regions other than the primary service region.

        Also returns True if there is no service_mapping (i.e. this is not a known global service).
        """
        if self.service_mapping is None:
            return True
        return self._service_details.get('regionalResources', False)

    @property
    def _service_details(self) -> dict:
        """Return the dictionary specifying details about the global service."""
        return self.service_mapping.get('service', {})

    def get_resource_region(self, resource: ResourceModel, default_region: str) -> str:
        """Get the region of a :class:`boto3.resources.base.ServiceResource` object.

        Arguments:
            resource (boto3.resources.base.ServiceResource): The :class:`~boto3.resources.base.ServiceResource`
                to find the region of.
            default_region (str): The region to return if there is no gloabl service mapping for this resource type.
        """
        if self.service_mapping is None:
            return default_region
        resource_type = botocore.xform_name(resource.meta.resource_model.shape)
        try:
            resource_mapping = self._get_resource_mapping(resource_type)
        except GlobalServiceResourceMappingNotFound:
            return self.service_mapping.get('service', {}).get('region')
        return self._get_region_from_operation(resource, resource_mapping)

    def _get_region_from_operation(self, resource: ResourceModel, resource_mapping: dict) -> str:
        request_mapping = resource_mapping['regionRequest']
        method = getattr(self.boto3_client, request_mapping['operation'])
        result = method(**self._build_params(resource, request_mapping['params']))
        return jmespath.search(request_mapping['pathToRegion'], result) or request_mapping.get('defaultValue', None)

    def _build_params(self, resource: ResourceModel, param_mappings: dict) -> dict:
        params = {}
        for param_mapping in param_mappings:
            key = param_mapping['target']
            params[key] = self._get_param_value(resource, param_mapping)
        return params

    def _get_param_value(self, resource: ResourceModel, param_mapping: dict) -> Any:
        if param_mapping['source'] == 'resourceAttribute':
            return getattr(resource, param_mapping['name'])
        raise AttributeError(f"Invalid param source {param_mapping['source']}")

    def _get_resource_mapping(self, resource_type: str) -> ResourceModel:
        if resource_type not in self.service_mapping.get('resources', []):
            raise GlobalServiceResourceMappingNotFound(
                f"Global resource mapping not found for {self.service_name} {resource_type}")
        return self.service_mapping['resources'][resource_type]


class GlobalServiceResourceMappingNotFound(Exception):
    """Global Service Resource Mapping not Found."""
    pass
