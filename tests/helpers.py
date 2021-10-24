import logging
import os
import re
from typing import Any, List, NamedTuple, Union

import boto3
from jmespath.lexer import LexerError

from cloudwanderer import URN
from cloudwanderer.cloud_wanderer_resource import CloudWandererResource

DEFAULT_SESSION = boto3.Session(aws_access_key_id="11111111", aws_secret_access_key="111111", aws_session_token="1111")
logger = logging.getLogger(__file__)


def filter_collections(collections, service_resource):
    for collection in collections:
        if service_resource.meta.resource_model.name == collection.meta.service_name:
            yield collection


# class TestStorageConnectorReadMixin:
def has_matching_urn(iterable, **kwargs):
    matches = []
    for resource in iterable:
        attribute_results = []
        for key, value in kwargs.items():
            attribute_results.append(getattr(resource.urn, key) == value)
        if all(attribute_results):
            matches.append(resource.urn)
    return matches


def assert_has_matching_urns(iterable, urns):
    """Assert that iterable has URNs that match the list of dicts in urns

    Arguments:
        iterable (iterable):
            An iterable containing URN objects
        urns (list):
            List of dictionaries whose key match aws urn attributes that must
            exist in at least one urn in iterable.
    """
    iterable = list(iterable)
    for urn in urns:
        assert has_matching_urn(iterable, **urn), f"{urn} not in {iterable}"


def assert_does_not_have_matching_urns(iterable, urns):
    """Assert that iterable does not have URNs that match the list of dicts in urns

    Arguments:
        iterable (iterable):
            An iterable containing URN objects
        urns (list):
            List of dictionaries whose keys should not match aws urn attributes that must
            exist in at least one urn in iterable.
    """
    iterable = list(iterable)
    for urn in urns:
        assert not has_matching_urn(iterable, **urn), f"{urn} is in {iterable}"


class ItemResult(NamedTuple):
    result: bool
    expected_value: Any
    received_value: Any


class OverlapResult(NamedTuple):
    expected_item: Any
    received_item: Any
    results: List[ItemResult]

    def __repr__(self):
        return (
            f"\nExpected\n\t{self.expected_item}\n"
            f"got\n\t{self.received_item}\n"
            f"differing on:\n\t{[x for x in self.results if not x.result]}"
        )


class GenericAssertionHelpers:
    def assert_dictionary_overlap(self, received, expected):
        """Asserts that every item in expected has an equivalent item in received.

        Where all key/values from the received item exist in the expected item.
        """
        received = received if isinstance(received, list) else list(received)
        unmatched, _, partial_matches = self.get_resource_overlap(received, expected)
        if unmatched and partial_matches:
            assert False, f"{partial_matches}"
        assert unmatched == [], f"\n\t{unmatched}\n was not found in\n\t{received}"

    def assert_no_dictionary_overlap(self, received, expected):
        """Asserts that NO item in expected has an equivalent item in received."""
        received = received if isinstance(received, list) else list(received)
        _, matched, _ = self.get_resource_overlap(received, expected)
        self.assertEqual(matched, [], f"{matched} was found in {received}")

    def get_resource_overlap(self, received, expected):
        """Returns CloudWandererResources/dicts from received that match the keys in the list of dicts in expected."""
        remaining = expected.copy()
        matched = []
        partial_matches = []
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
                        matching.append(
                            ItemResult(
                                result=bool(
                                    re.match(expected_value, received_value) or expected_value == received_value
                                ),
                                expected_value=expected_value,
                                received_value=received_value,
                            )
                        )
                    else:
                        matching.append(
                            ItemResult(
                                result=expected_value == received_value,
                                expected_value=expected_value,
                                received_value=received_value,
                            )
                        )

                if all([x.result for x in matching]):
                    remaining.remove(expected_item)
                    matched.append(expected_item)
                    break
                if any(x.result for x in matching):
                    partial_matches.append(
                        OverlapResult(received_item=received_item, expected_item=expected_item, results=matching)
                    )

        return remaining, matched, partial_matches

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
            value = getattr(resource, key)
            if isinstance(value, URN):
                return str(value)
            return value
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


# class SetupMocking:
#     default_moto_services = ["mock_ec2", "mock_iam", "mock_sts", "mock_s3", "mock_dynamodb2"]

#     def __init__(self):
#         self.services_mock = PropertyMock()
#         self.services_patcher = patch(
#             "cloudwanderer.boto3_services.Boto3Services.available_services",
#             new=self.services_mock,
#         )
#         self.limit_resources = PropertyMock(return_value=[])
#         self.collections_patcher = patch(
#             "cloudwanderer.aws_interface.CloudWandererAWSInterface.limit_resources", new=self.limit_resources
#         )
#         self.service_mocks = {}
#         self.regions_mock = PropertyMock(return_value=[])
#         self.regions_patcher = patch("moto.ec2.models.RegionsAndZonesBackend.regions", new=self.regions_mock)
#         clear_aws_credentials()

#     def start_general_mock(
#         self, restrict_regions: list = None, restrict_services: bool = True, limit_resources: list = None
#     ):
#         restrict_regions = ["eu-west-2", "us-east-1"] if restrict_regions is None else restrict_regions
#         if restrict_regions:
#             self.start_restrict_regions(regions=restrict_regions)
#         if restrict_services:
#             self.start_restrict_services(services=["ec2", "s3", "iam"])
#         if limit_resources is not False:
#             self.start_limit_resources(limit_resources)
#         self.start_moto_services()

#     def stop_general_mock(self):
#         stop_methods = [
#             self.stop_moto_services,
#             self.stop_restrict_services,
#             self.stop_limit_collections_list,
#             self.stop_restrict_regions,
#         ]
#         for method in stop_methods:
#             try:
#                 method()
#             except RuntimeError:
#                 pass

#     def start_restrict_services(self, services: List[str]) -> None:
#         self.services_mock.return_value = services
#         self.services_patcher.start()

#     def stop_restrict_services(self) -> None:
#         self.services_patcher.stop()

#     def start_moto_services(self, services=None):
#         services = self.default_moto_services + (services or [])
#         for service in services:
#             if service not in self.service_mocks:
#                 self.service_mocks[service] = getattr(moto, service)()
#             self.service_mocks[service].start()

#     def stop_moto_services(self):
#         for service in self.service_mocks.values():
#             service.stop()
#         self.service_mocks = {}

#     def start_limit_resources(self, limit_resources):
#         """Limit the boto3 resources we service to a subset we use for testing."""

#         self.limit_resources.return_value = limit_resources or [
#             "ec2:instance",
#             "ec2:vpc",
#             "s3:bucket",
#             "iam:group",
#             "iam:role",
#         ]
#         self.collections_patcher.start()

#     def stop_limit_collections_list(self):
#         self.collections_patcher.stop()

#     def start_restrict_regions(self, regions):
#         self.regions_mock.return_value = [
#             ec2.models.Region(region_name, "ec2.{region_name}.amazonaws.com", "opt-in-not-required")
#             for region_name in regions
#         ]
#         self.regions_patcher.start()

#     def stop_restrict_regions(self):
#         self.regions_patcher.stop()


# DEFAULT_MOCKER = None


# def get_default_mocker():
#     global DEFAULT_MOCKER
#     if not DEFAULT_MOCKER:
#         DEFAULT_MOCKER = SetupMocking()
#     return DEFAULT_MOCKER
