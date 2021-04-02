import logging
import sys
from abc import ABC
from typing import Any, Dict, List, NamedTuple

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

from unittest.mock import MagicMock, patch

import boto3

from cloudwanderer import URN, CloudWanderer
from cloudwanderer.aws_interface import CloudWandererAWSInterface
from cloudwanderer.exceptions import UnsupportedResourceTypeError
from cloudwanderer.storage_connectors import MemoryStorageConnector

from ..helpers import DEFAULT_SESSION, GenericAssertionHelpers


class NoMotoMock(ABC, GenericAssertionHelpers):
    single_resource_scenarios: List["SingleResourceScenario"]
    multiple_resource_scenarios = List["MultipleResourceScenario"]

    def setUp(self):
        self.storage_connector = MemoryStorageConnector()
        self.wanderer = CloudWanderer(
            storage_connectors=[self.storage_connector],
            cloud_interface=CloudWandererAWSInterface(DEFAULT_SESSION),
        )
        self.boto3_client_mock = MagicMock()
        self.add_service_mock()
        self.add_caller_identity()
        self.client_patch = patch("boto3.session.Session.client", new=self.boto3_client_mock)
        self.client_patch.start()

    def tearDown(self) -> None:
        self.client_patch.stop()

    def add_caller_identity(self):
        self.service_mocks["sts"] = MagicMock(**{"get_caller_identity.return_value": {"Account": "123456789012"}})

    def add_service_mock(self):
        self.service_mocks = {}
        for service_name in self.wanderer.cloud_interface.boto3_services.available_services:
            self.service_mocks[service_name] = MagicMock(**self.mock.get(service_name, {}))
            self.service_mocks[service_name].meta = boto3.client(service_name).meta
        self.boto3_client_mock.side_effect = lambda service_name, **kwargs: self.service_mocks[service_name]

    def test_write_resource(self):
        for scenario in self.single_resource_scenarios:
            logging.info("Testing fetching %s", scenario.urn)

            if issubclass(scenario.expected_results, UnsupportedResourceTypeError):
                with self.assertRaises(UnsupportedResourceTypeError):
                    self.wanderer.write_resource(urn=scenario.urn)
                continue

            self.wanderer.write_resource(urn=scenario.urn)
            self.assert_dictionary_overlap(
                self.storage_connector.read_all(),
                scenario.expected_results,
            )

    def test_write_resources(self):
        for scenario in self.multiple_resource_scenarios:
            self.wanderer.write_resources(**scenario.arguments)
            self.assert_dictionary_overlap(
                self.storage_connector.read_all(),
                scenario.expected_results,
            )


class SingleResourceScenario(NamedTuple):
    urn: URN
    expected_results: List[Dict[str, Any]]


class MultipleResourceScenario(NamedTuple):
    arguments: List["CloudWandererCalls"]
    expected_results: List[Dict[str, Any]]


class CloudWandererCalls(TypedDict, total=False):
    regions: List[str]
    service_names: List[str]
    resource_types: List[str]
