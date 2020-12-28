import os
from unittest.mock import patch, MagicMock
import functools
import cloudwanderer
from .mocks import generate_mock_session
from moto import ec2, mock_ec2, mock_iam, mock_sts, mock_s3, mock_dynamodb2
import boto3


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


class TestStorageConnectorReadMixin:
    def has_matching_aws_urn(self, iterable, **kwargs):
        matches = []
        for resource in iterable:
            attribute_results = []
            for key, value in kwargs.items():
                attribute_results.append(getattr(resource.urn, key) == value)
            if all(attribute_results):
                matches.append(resource.urn)
        return matches

    def assert_has_matching_aws_urns(self, iterable, aws_urns):
        """Assert that iterable has AwsUrns that match the list of dicts in aws_urns
        Arguments:
            iterable (iterable):
                An iterable containing AwsUrn objects
            aws_urns (list):
                List of dictionaries whose key match aws urn attributes that must
                exist in at least one urn in iterable.
        """
        iterable = list(iterable)
        for urn in aws_urns:
            self.assertTrue(self.has_matching_aws_urn(iterable, **urn),
                            f"{urn} not in {iterable}"
                            )

    def assert_does_not_have_matching_aws_urns(self, iterable, aws_urns):
        """Assert that iterable does not have AwsUrns that match the list of dicts in aws_urns
        Arguments:
            iterable (iterable):
                An iterable containing AwsUrn objects
            aws_urns (list):
                List of dictionaries whose keys should not match aws urn attributes that must
                exist in at least one urn in iterable.
        """
        iterable = list(iterable)
        for urn in aws_urns:
            self.assertFalse(
                self.has_matching_aws_urn(iterable, **urn),
                f"{urn} is in {iterable}"
            )


def limit_collections_list():
    """Limit the boto3 resource collections we service to a subset we use for testing."""
    collections_to_mock = [
        ('ec2', ('instance', 'instances')),
        ('ec2', ('vpc', 'vpcs')),
        ('s3', ('bucket', 'buckets')),
        ('iam', ('group', 'groups'))
    ]
    mock_collections = []
    for service, name_tuple in collections_to_mock:
        collection = MagicMock(**{
            'meta.service_name': service,
            'resource.model.shape': name_tuple[0]
        })
        collection.configure_mock(name=name_tuple[1])
        mock_collections.append(collection)
    cloudwanderer.cloud_wanderer.CloudWandererBoto3Interface.get_resource_collections = MagicMock(
        side_effect=lambda service_resource: [
            collection
            for collection in mock_collections
            if service_resource.meta.service_name == collection.meta.service_name
        ]
    )


def mock_services():
    for service in [mock_ec2, mock_iam, mock_sts, mock_s3, mock_dynamodb2]:
        mock = service()
        mock.start()


def setup_moto():
    os.environ['AWS_ACCESS_KEY_ID'] = '1111111'
    os.environ['AWS_SECRET_ACCESS_KEY'] = '1111111'
    os.environ['AWS_SESSION_TOKEN'] = '1111111'
    os.environ['AWS_DEFAULT_REGION'] = 'eu-west-2'
    ec2.models.RegionsAndZonesBackend.regions = [
        ec2.models.Region(region_name, "ec2.{region_name}.amazonaws.com", "opt-in-not-required")
        for region_name in ['eu-west-2', 'us-east-1']
    ]
    cloudwanderer.cloud_wanderer.CloudWandererBoto3Interface.get_all_resource_services = MagicMock(
        return_value=[boto3.resource(service) for service in ['ec2', 's3', 'iam']])
    limit_collections_list()
    mock_services()
