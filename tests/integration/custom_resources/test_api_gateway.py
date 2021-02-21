import unittest

import boto3

from cloudwanderer import URN, CloudWanderer
from cloudwanderer.storage_connectors import MemoryStorageConnector

from ..helpers import GenericAssertionHelpers, get_default_mocker


class TestSecretsManagerResources(unittest.TestCase, GenericAssertionHelpers):
    def setUp(self):
        get_default_mocker().start_moto_services(["mock_sts", "mock_apigateway"])
        self.storage_connector = MemoryStorageConnector()
        self.wanderer = CloudWanderer(storage_connectors=[self.storage_connector])
        apigateway = boto3.client("apigateway")
        apigateway.create_rest_api(
            name="TestApi",
        )
        self.rest_apis = apigateway.get_rest_apis()

    def tearDown(self):
        get_default_mocker().stop_moto_services()

    def test_get_rest_api(self):

        self.wanderer.write_resource(
            urn=URN(
                account_id=self.wanderer.cloud_interface.account_id,
                region="eu-west-2",
                service="apigateway",
                resource_type="rest_api",
                resource_id=self.rest_apis["items"][0]["id"],
            )
        )

        self.assert_dictionary_overlap(
            self.storage_connector.read_all(),
            [{"name": "TestApi", "apiKeySource": "HEADER", "endpointConfiguration": {"types": ["EDGE"]}, "tags": {}}],
        )

    def test_get_rest_apis(self):

        self.wanderer.write_resources(regions=["eu-west-2"], service_names=["apigateway"])

        self.assert_dictionary_overlap(
            self.storage_connector.read_all(),
            [{"name": "TestApi", "apiKeySource": "HEADER", "endpointConfiguration": {"types": ["EDGE"]}, "tags": {}}],
        )
