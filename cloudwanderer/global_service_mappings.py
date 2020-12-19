"""Provides a way to map global resources back to the regions they reside in.

Most well-known example of this is s3 buckets which require an additional API call to get their region.
"""
import os
import pathlib
import json
import boto3
import botocore
import jmespath


class GlobalServiceMappingCollection:

    def __init__(self, boto3_session=None):
        self.boto3_session = boto3_session or boto3.Session()
        self.factory = GlobalServiceMapping
        self.global_service_mappings_path = os.path.join(
            pathlib.Path(__file__).parent.absolute(),
            'global_service_mappings'
        )
        self._global_service_maps = None

    def get_global_service_map(self, service_name):
        """Returns the mapping for service_name."""
        if self._global_service_maps is None:
            self._global_service_maps = self.get_global_service_maps()
        return self._global_service_maps.get(
            service_name,
            GlobalServiceMapping(
                service_name=service_name,
                service_mapping=None,
                boto3_session=self.boto3_session
            )
        )

    def get_global_service_maps(self):
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

    def _load_global_service_mapping(self, service_name):
        with open(os.path.join(self.global_service_mappings_path, f"{service_name}.json")) as definition_path:
            return json.load(definition_path)

    def _list_global_service_mappings(self):
        return [
            file_name.replace('.json', '')
            for file_name in os.listdir(self.global_service_mappings_path)
            if os.path.isfile(os.path.join(self.global_service_mappings_path, file_name))
        ]


class GlobalServiceMapping:

    def __init__(self, service_name, service_mapping, boto3_session=None):
        self.boto3_session = boto3_session or boto3.Session()
        self.service_name = service_name
        self.service_mapping = service_mapping
        self.boto3_client = self.boto3_session.client(service_name)

    def get_resource_region(self, resource):
        """Get the region of a boto3.Resource object."""
        if self.service_mapping is None:
            return self.boto3_session.region_name
        resource_type = botocore.xform_name(resource.meta.resource_model.shape)
        try:
            resource_mapping = self._get_resource_mapping(resource_type)
        except GlobalServiceResourceMappingNotFound:
            return self.service_mapping.get('service', {}).get('region')
        return self._get_region_from_operation(resource, resource_mapping)

    def _get_region_from_operation(self, resource, resource_mapping):
        request_mapping = resource_mapping['regionRequest']
        method = getattr(self.boto3_client, request_mapping['operation'])
        result = method(**self._build_params(resource, request_mapping['params']))
        return jmespath.search(request_mapping['pathToRegion'], result) or request_mapping.get('defaultValue', None)

    def _build_params(self, resource, param_mappings):
        params = {}
        for param_mapping in param_mappings:
            key = param_mapping['target']
            params[key] = self._get_param_value(resource, param_mapping)
        return params

    def _get_param_value(self, resource, param_mapping):
        if param_mapping['source'] == 'resourceAttribute':
            return getattr(resource, param_mapping['name'])
        raise AttributeError(f"Invalid param source {param_mapping['source']}")

    def _get_resource_mapping(self, resource_type):
        if resource_type not in self.service_mapping.get('resources', []):
            raise GlobalServiceResourceMappingNotFound(
                f"Global resource mapping not found for {self.service_name} {resource_type}")
        return self.service_mapping['resources'][resource_type]


class GlobalServiceMappingNotFound(Exception):
    pass


class GlobalServiceResourceMappingNotFound(Exception):
    pass
