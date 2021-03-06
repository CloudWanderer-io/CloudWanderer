import logging
import sys
from abc import ABC
from typing import Any, Dict, List, NamedTuple, Optional, Union

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

from unittest.mock import MagicMock, patch

import boto3

from cloudwanderer import URN, CloudWanderer
from cloudwanderer.aws_interface import CloudWandererAWSInterface
from cloudwanderer.storage_connectors import MemoryStorageConnector

from ..helpers import DEFAULT_SESSION, GenericAssertionHelpers

logger = logging.getLogger(__name__)


def paginator_side_effect(mock_dict):
    def side_effect(method_name, **kwargs):
        for method_path, mock_return in mock_dict.items():
            path_parts = method_path.split(".")
            mocked_method_name = path_parts[0]
            return_type = path_parts[1]
            if mocked_method_name == method_name:
                return MagicMock(paginate=MagicMock(**{return_type: [mock_return]}))
        return MagicMock()

    return side_effect


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
            self.service_mocks[service_name] = MagicMock()
            for method_path, mock_return in self.mock.get(service_name, {}).items():
                path_parts = method_path.split(".")
                method_name = path_parts[0]
                return_type = path_parts[1]
                logger.info(f"Adding mock for {service_name} {method_name}")
                setattr(self.service_mocks[service_name], method_name, MagicMock(**{return_type: mock_return}))
            self.service_mocks[service_name].get_paginator.side_effect = paginator_side_effect(
                self.mock.get(service_name, {})
            )

            self.service_mocks[service_name].meta = boto3.client(service_name).meta
        self.boto3_client_mock.side_effect = lambda service_name, **kwargs: self.service_mocks[service_name]

    def test_write_resource(self):
        for i, scenario in enumerate(self.single_resource_scenarios):
            logging.info("Testing fetching %s", scenario.urn)

            if isinstance(scenario.expected_results, type):
                with self.assertRaises(scenario.expected_results):
                    self.wanderer.write_resource(urn=scenario.urn)
                continue

            self.wanderer.write_resource(urn=scenario.urn)
            self.assert_dictionary_overlap(
                self.storage_connector.read_all(),
                scenario.expected_results,
            )
            if scenario.expected_call is None:
                continue
            mock_method = getattr(self.service_mocks[scenario.expected_call.service], scenario.expected_call.method)
            mock_method.assert_called_with(*scenario.expected_call.args, **scenario.expected_call.kwargs)

    def test_write_resources(self):
        for scenario in self.multiple_resource_scenarios:
            self.wanderer.write_resources(**scenario.arguments)
            self.assert_dictionary_overlap(
                self.storage_connector.read_all(),
                scenario.expected_results,
            )


class SingleResourceScenario(NamedTuple):
    urn: URN
    expected_results: List[Union[Dict[str, Any], type]]
    expected_call: Optional["ExpectedCall"] = None


class ExpectedCall(NamedTuple):
    service: str
    method: str
    args: List[Any]
    kwargs: Dict[str, Any]


class MultipleResourceScenario(NamedTuple):
    arguments: List["CloudWandererCalls"]
    expected_results: List[Dict[str, Any]]


class CloudWandererCalls(TypedDict, total=False):
    regions: List[str]
    service_names: List[str]
    resource_types: List[str]
