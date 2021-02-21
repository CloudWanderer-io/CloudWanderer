import logging
import os
import re
from typing import List, Union
from unittest.mock import MagicMock, patch

import boto3
import moto
from botocore import xform_name
from jmespath.lexer import LexerError
from moto import ec2

import cloudwanderer
from cloudwanderer.boto3_helpers import get_resource_collections, get_service_resource_types_from_collections
from cloudwanderer.cloud_wanderer_resource import CloudWandererResource
from cloudwanderer.service_mappings import GlobalServiceResourceMappingNotFoundError, ServiceMappingCollection

from .mocks import generate_mock_collection

DEFAULT_SESSION = boto3.Session(aws_access_key_id="11111111", aws_secret_access_key="111111", aws_session_token="1111")
logger = logging.getLogger(__file__)


def filter_collections(collections, service_resource):
    for collection in collections:
        if service_resource.meta.resource_model.name == collection.meta.service_name:
            yield collection


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
            self.assertTrue(self.has_matching_aws_urn(iterable, **urn), f"{urn} not in {iterable}")

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
            self.assertFalse(self.has_matching_aws_urn(iterable, **urn), f"{urn} is in {iterable}")


class GenericAssertionHelpers:
    def assert_dictionary_overlap(self, received, expected):
        """Asserts that every item in expected has an equivalent item in received.

        Where all key/values from the received item exist in the expected item.
        """
        received = received if isinstance(received, list) else list(received)
        unmatched, _ = self.get_resource_overlap(received, expected)
        self.assertEqual(unmatched, [], f"{unmatched} was not found in {received}")

    def assert_no_dictionary_overlap(self, received, expected):
        """Asserts that NO item in expected has an equivalent item in received."""
        received = received if isinstance(received, list) else list(received)
        _, matched = self.get_resource_overlap(received, expected)
        self.assertEqual(matched, [], f"{matched} was found in {received}")

    def get_resource_overlap(self, received, expected):
        """Returns CloudWandererResources/dicts from received that match the keys in the list of dicts in expected."""
        remaining = expected.copy()
        matched = []
        for received_item in received:
            for expected_item in expected:
                if expected_item not in remaining:
                    continue
                matching = []
                for key, expected_value in expected_item.items():
                    if isinstance(received_item, dict):
                        received_value = received_item.get(key)
                    if isinstance(received_item, CloudWandererResource):
                        try:
                            received_value = self._get_key_from_resource(received_item, key)
                        except KeyError:
                            continue
                    if isinstance(received_value, str) and isinstance(expected_value, str):
                        # Allow regex matching of strings (as moto randomly generates resource IDs)
                        matching.append(re.match(expected_value, received_value))
                    else:
                        matching.append(expected_value == received_value)

                if all(matching):
                    remaining.remove(expected_item)
                    matched.append(expected_item)
                    break
        return remaining, matched

    def get_secondary_attributes_from_resources(self, resources: list):
        return [
            secondary_attribute
            for resource in resources
            for secondary_attribute in resource.cloudwanderer_metadata.secondary_attributes
        ]

    def _get_key_from_resource(self, resource, key) -> Union[str, list]:
        """Key should either be an attribute name or a valid secondary attribute JMESPath.

        Raises:
            KeyError: Occurs when the key does not exist
        """
        try:
            return str(getattr(resource, key))
        except AttributeError:
            try:
                return resource.get_secondary_attribute(jmes_path=key)
            except LexerError:
                pass
        raise KeyError(f"{key} missing from {resource}")


def clear_aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "1111111"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "1111111"
    os.environ["AWS_SESSION_TOKEN"] = "1111111"
    os.environ["AWS_DEFAULT_REGION"] = "eu-west-2"


class SetupMocking:
    default_moto_services = ["mock_ec2", "mock_iam", "mock_sts", "mock_s3", "mock_dynamodb2"]

    def __init__(self):
        self.services_mock = MagicMock()
        self.services_patcher = patch(
            "cloudwanderer.custom_resource_definitions.CustomResourceDefinitions.get_all_resource_services",
            new=self.services_mock,
        )
        self.collections_mock = MagicMock()
        self.collections_patcher = patch(
            "cloudwanderer.custom_resource_definitions.get_resource_collections", new=self.collections_mock
        )
        self.service_mocks = {}
        clear_aws_credentials()

    def start_general_mock(
        self, restrict_regions: list = None, restrict_services: bool = True, restrict_collections: list = None
    ):
        restrict_regions = ["eu-west-2", "us-east-1"] if restrict_regions is None else restrict_regions
        if restrict_regions:
            ec2.models.RegionsAndZonesBackend.regions = [
                ec2.models.Region(region_name, "ec2.{region_name}.amazonaws.com", "opt-in-not-required")
                for region_name in restrict_regions
            ]
        if restrict_services:
            self.start_restrict_services(services=["ec2", "s3", "iam"])
        if restrict_collections is not False:
            self.start_limit_collections_list(restrict_collections)
        self.start_moto_services()

    def stop_general_mock(self):
        stop_methods = [self.stop_moto_services, self.stop_restrict_services, self.stop_limit_collections_list]
        for method in stop_methods:
            try:
                method()
            except RuntimeError:
                pass

    def start_restrict_services(self, services: List[str]) -> None:
        self.services_mock.return_value = [boto3.resource(service) for service in services]
        self.services_patcher.start()

    def stop_restrict_services(self) -> None:
        self.services_patcher.stop()

    def start_moto_services(self, services=None):
        services = self.default_moto_services + (services or [])
        for service in services:
            if service not in self.service_mocks:
                self.service_mocks[service] = getattr(moto, service)()
            self.service_mocks[service].start()

    def stop_moto_services(self):
        for service in self.service_mocks.values():
            service.stop()
        self.service_mocks = {}

    def start_limit_collections_list(self, restrict_collections):
        """Limit the boto3 resource collections we service to a subset we use for testing."""
        if not restrict_collections:
            collections_to_mock = [
                ("ec2", ("instance", "instances")),
                ("ec2", ("vpc", "vpcs")),
                ("s3", ("bucket", "buckets")),
                ("iam", ("group", "groups")),
                ("iam", ("Role", "roles")),
                ("Role", ("RolePolicy", "policies")),
            ]
            restrict_collections = []
            for service, name_tuple in collections_to_mock:
                restrict_collections.append(generate_mock_collection(service, name_tuple[0], name_tuple[1]))
        logger.debug("Mocking collections: %s", restrict_collections)
        self.collections_mock.side_effect = lambda boto3_service: filter_collections(
            restrict_collections, boto3_service
        )
        self.collections_patcher.start()

    def stop_limit_collections_list(self):
        self.collections_patcher.stop()


DEFAULT_MOCKER = None


def get_default_mocker():
    global DEFAULT_MOCKER
    if not DEFAULT_MOCKER:
        DEFAULT_MOCKER = SetupMocking()
    return DEFAULT_MOCKER


def get_secondary_attribute_types(service_name):
    boto3_interface = cloudwanderer.boto3_interface.CloudWandererBoto3Interface(boto3_session=DEFAULT_SESSION)
    service_maps = ServiceMappingCollection(boto3_session=DEFAULT_SESSION)
    service_map = service_maps.get_service_mapping(service_name=service_name)
    resource_types = get_service_resource_types_from_collections(
        get_resource_collections(
            boto3_service=boto3_interface.boto3_getter.custom_resource_definitions.resource(service_name=service_name)
        )
    )
    for resource_type in resource_types:
        try:
            resource_map = service_map.get_resource_mapping(resource_type=resource_type)
        except GlobalServiceResourceMappingNotFoundError:
            continue
        for secondary_attribute in resource_map.secondary_attributes:
            yield (xform_name(resource_type), xform_name(secondary_attribute))
