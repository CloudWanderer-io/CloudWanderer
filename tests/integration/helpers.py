import os
import logging
from unittest.mock import patch, MagicMock
import functools
from botocore import xform_name
import cloudwanderer
from cloudwanderer.service_mappings import ServiceMappingCollection, GlobalServiceResourceMappingNotFound
from .mocks import generate_mock_session, generate_mock_collection
from moto import ec2, mock_ec2, mock_iam, mock_sts, mock_s3, mock_dynamodb2
import boto3

DEFAULT_SESSION = boto3.Session()
logger = logging.getLogger(__file__)


def filter_collections(collections, service_resource):
    for collection in collections:
        if service_resource.meta.resource_model.name == collection.meta.service_name:
            yield collection


def patch_resource_collections(collections):
    def decorator_patch_resource_collections(func):
        @functools.wraps(func)
        def wrapper_patch_resource_collections(*args, **kwargs):
            with patch.object(
                cloudwanderer.cloud_wanderer.CloudWandererBoto3Interface,
                'get_resource_collections',
                new=MagicMock(side_effect=lambda boto3_service: filter_collections(collections, boto3_service))
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
        self.assertFalse(
            self.storage_connector_write_resource_called_with(**kwargs),
            f"Found match for {kwargs} in {self.mock_storage_connector.write_resource.call_args_list}"
        )

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

    def assert_storage_connector_write_secondary_attribute_not_called_with(self, **kwargs):
        assert not self.storage_connector_write_secondary_attribute_called_with(**kwargs)

    def assert_storage_connector_write_secondary_attribute_called_with(self, **kwargs):
        self.assertTrue(
            self.storage_connector_write_secondary_attribute_called_with(**kwargs),
            f"No match for {kwargs} in {self.mock_storage_connector.write_secondary_attribute.call_args_list}"
        )

    def storage_connector_write_secondary_attribute_called_with(
            self, region, service, resource_type, response_dict, attribute_type):
        matches = []
        for write_secondary_attribute_call in self.mock_storage_connector.write_secondary_attribute.call_args_list:
            call_dict = write_secondary_attribute_call[1]
            comparisons = []
            for var in ['region', 'service', 'resource_type']:
                comparisons.append(eval(var) == getattr(call_dict['urn'], var))
            for attr, value in response_dict.items():
                try:
                    comparisons.append(call_dict['secondary_attribute'].meta.data[attr] == value)
                except KeyError:
                    comparisons.append(False)
            comparisons.append(attribute_type == call_dict['attribute_type'])
            if all(comparisons):
                matches.append((call_dict['urn'], call_dict['secondary_attribute']))
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
            self.assertTrue(
                self.has_matching_aws_urn(iterable, **urn),
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


def limit_collections_list(restrict_collections):
    """Limit the boto3 resource collections we service to a subset we use for testing."""
    if not restrict_collections:
        collections_to_mock = [
            ('ec2', ('instance', 'instances')),
            ('ec2', ('vpc', 'vpcs')),
            ('s3', ('bucket', 'buckets')),
            ('iam', ('group', 'groups')),
            ('iam', ('Role', 'roles')),
            ('Role', ('RolePolicy', 'policies'))
        ]
        restrict_collections = []
        for service, name_tuple in collections_to_mock:
            restrict_collections.append(generate_mock_collection(service, name_tuple[0], name_tuple[1]))
    logger.debug('Mocking collections: %s', restrict_collections)
    cloudwanderer.cloud_wanderer.CloudWandererBoto3Interface.get_resource_collections = MagicMock(
        side_effect=lambda boto3_service: filter_collections(restrict_collections, boto3_service)
    )


def mock_services():
    for service in [mock_ec2, mock_iam, mock_sts, mock_s3, mock_dynamodb2]:
        mock = service()
        mock.start()


def setup_moto(restrict_regions: list = None, restrict_services: bool = True,
               restrict_collections: list = None):
    os.environ['AWS_ACCESS_KEY_ID'] = '1111111'
    os.environ['AWS_SECRET_ACCESS_KEY'] = '1111111'
    os.environ['AWS_SESSION_TOKEN'] = '1111111'
    os.environ['AWS_DEFAULT_REGION'] = 'eu-west-2'
    restrict_regions = ['eu-west-2', 'us-east-1'] if restrict_regions is None else restrict_regions
    if restrict_regions:
        ec2.models.RegionsAndZonesBackend.regions = [
            ec2.models.Region(region_name, "ec2.{region_name}.amazonaws.com", "opt-in-not-required")
            for region_name in restrict_regions
        ]
    if restrict_services:
        cloudwanderer.cloud_wanderer.CloudWandererBoto3Interface.get_all_resource_services = MagicMock(
            return_value=[boto3.resource(service) for service in ['ec2', 's3', 'iam']])
    if restrict_collections is not False:
        limit_collections_list(restrict_collections)
    mock_services()


def get_secondary_attribute_types(service_name):
    boto3_interface = cloudwanderer.boto3_interface.CloudWandererBoto3Interface(boto3_session=DEFAULT_SESSION)
    service_maps = ServiceMappingCollection(boto3_session=DEFAULT_SESSION)
    service_map = service_maps.get_service_mapping(service_name=service_name)
    resource_types = boto3_interface.get_service_resource_types_from_collections(
        boto3_interface.get_resource_collections(
            boto3_service=boto3_interface.get_resource_service_by_name(
                service_name=service_name
            )
        )
    )
    for resource_type in resource_types:
        try:
            resource_map = service_map.get_resource_mapping(resource_type=resource_type)
        except GlobalServiceResourceMappingNotFound:
            continue
        for secondary_attribute in resource_map.secondary_attributes:
            yield (
                xform_name(resource_type),
                xform_name(secondary_attribute)
            )
