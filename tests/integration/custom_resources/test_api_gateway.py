import unittest
import boto3
from cloudwanderer import CloudWanderer
from cloudwanderer.storage_connectors import MemoryStorageConnector
from ..helpers import get_default_mocker, GenericAssertionHelpers


class TestSecretsManagerResources(unittest.TestCase, GenericAssertionHelpers):

    @classmethod
    def setUpClass(cls):
        get_default_mocker().start_moto_services(['mock_sts', 'mock_apigateway'])

    @classmethod
    def tearDownClass(cls):
        get_default_mocker().stop_moto_services()

    def setUp(self):
        self.storage_connector = MemoryStorageConnector()
        self.wanderer = CloudWanderer(
            storage_connectors=[self.storage_connector]
        )

    def test_rest_api(self):
        apigateway = boto3.client('apigateway')
        apigateway.create_rest_api(
            name='TestApi',
        )
        print(apigateway.get_rest_apis())

        self.wanderer.write_resources_of_service_in_region(region_name='eu-west-2', service_name='apigateway')

        self.assert_dictionary_overlap(self.storage_connector.read_all(), [
            {
                'name': 'TestApi',
                'apiKeySource': 'HEADER',
                'endpointConfiguration': {'types': ['EDGE']},
                'tags': {}
            }
        ])
