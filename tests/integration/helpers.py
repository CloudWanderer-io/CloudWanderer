from unittest.mock import patch, MagicMock
import functools
import cloudwanderer
from .mocks import generate_mock_session


def patch_resource_collections(collections):
    def decorator_patch_resource_collections(func):
        @functools.wraps(func)
        def wrapper_patch_resource_collections(*args, **kwargs):
            with patch.object(
                cloudwanderer.cloud_wanderer.CloudWandererBoto3Interface,
                'get_resource_collections',
                new=MagicMock(side_effect=lambda service_resource: [
                    collection
                    for collection in collections
                    if service_resource.meta.service_name == collection.meta.service_name
                ])
            ):
                return func(*args, **kwargs)
        return wrapper_patch_resource_collections
    return decorator_patch_resource_collections


def patch_services(services):
    def decorator_patch_services(func):
        @functools.wraps(func)
        def wrapper_patch_services(*args, **kwargs):
            with patch.object(
                cloudwanderer.cloud_wanderer.CloudWandererBoto3Interface,
                'get_all_resource_services',
                new=MagicMock(return_value=[generate_mock_session().resource(service) for service in services])
            ):
                return func(*args, **kwargs)
        return wrapper_patch_services
    return decorator_patch_services


class MockStorageConnectorMixin:
    """Mixin to simplify assertions against a mock storage connector.

    Expects the storage connector to be a ``MagicMock`` set as ``self.storage_connector``.
    """

    def assert_storage_connector_write_resource_not_called_with(self, **kwargs):
        assert not self.storage_connector_write_resource_called_with(**kwargs)

    def assert_storage_connector_write_resource_called_with(self, **kwargs):
        self.assertTrue(
            self.storage_connector_write_resource_called_with(**kwargs),
            f"No match for {kwargs} in {self.mock_storage_connector.write_resource.call_args_list}"
        )

    def storage_connector_write_resource_called_with(self, region, service, resource_type, attributes_dict):
        matches = []
        for write_resource_call in self.mock_storage_connector.write_resource.call_args_list:
            urn, resource = write_resource_call[0]
            comparisons = []
            for var in ['region', 'service', 'resource_type']:
                comparisons.append(eval(var) == getattr(urn, var))
            for attr, value in attributes_dict.items():
                try:
                    comparisons.append(getattr(resource, attr) == value)
                except AttributeError:
                    comparisons.append(False)
            if all(comparisons):
                matches.append((urn, resource))
        return matches

    def assert_storage_connector_write_resource_attribute_not_called_with(self, **kwargs):
        assert not self.storage_connector_write_resource_attribute_called_with(**kwargs)

    def assert_storage_connector_write_resource_attribute_called_with(self, **kwargs):
        self.assertTrue(
            self.storage_connector_write_resource_attribute_called_with(**kwargs),
            f"No match for {kwargs} in {self.mock_storage_connector.write_resource_attribute.call_args_list}"
        )

    def storage_connector_write_resource_attribute_called_with(
            self, region, service, resource_type, response_dict, attribute_type):
        matches = []
        for write_resource_attribute_call in self.mock_storage_connector.write_resource_attribute.call_args_list:
            call_dict = write_resource_attribute_call[1]
            comparisons = []
            for var in ['region', 'service', 'resource_type']:
                comparisons.append(eval(var) == getattr(call_dict['urn'], var))
            for attr, value in response_dict.items():
                try:
                    comparisons.append(call_dict['resource_attribute'].meta.data[attr] == value)
                except KeyError:
                    comparisons.append(False)
            comparisons.append(attribute_type == call_dict['attribute_type'])
            if all(comparisons):
                matches.append((call_dict['urn'], call_dict['resource_attribute']))
        return matches
