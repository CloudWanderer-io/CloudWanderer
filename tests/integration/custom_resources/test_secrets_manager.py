import unittest

import boto3

from cloudwanderer import URN, CloudWanderer
from cloudwanderer.storage_connectors import MemoryStorageConnector

from ..helpers import GenericAssertionHelpers, get_default_mocker


class TestSecretsManagerResources(unittest.TestCase, GenericAssertionHelpers):
    def setUp(self):
        get_default_mocker().start_moto_services(["mock_sts", "mock_secretsmanager"])
        self.storage_connector = MemoryStorageConnector()
        self.wanderer = CloudWanderer(storage_connectors=[self.storage_connector])
        secretsmanager = boto3.client("secretsmanager")
        secretsmanager.create_secret(Name="TestSecret", SecretString="Ssshhh")

    def tearDown(self) -> None:
        get_default_mocker().stop_moto_services()

    def test_write_secret(self):

        self.wanderer.write_resource(
            urn=URN(
                account_id=self.wanderer.cloud_interface.account_id,
                region="eu-west-2",
                service="secretsmanager",
                resource_type="secret",
                resource_id="TestSecret",
            )
        )

        self.assert_dictionary_overlap(
            self.storage_connector.read_all(),
            [
                {
                    "Name": "TestSecret",
                    "Description": None,
                    "KmsKeyId": None,
                    "RotationEnabled": False,
                    "RotationLambdaARN": None,
                    "RotationRules": {"AutomaticallyAfterDays": 0},
                    "Tags": [],
                }
            ],
        )

    def test_write_secrets(self):

        self.wanderer.write_resources(regions=["eu-west-2"], service_names=["secretsmanager"])

        self.assert_dictionary_overlap(
            self.storage_connector.read_all(),
            [
                {
                    "Name": "TestSecret",
                    "Description": None,
                    "KmsKeyId": None,
                    "RotationEnabled": False,
                    "RotationLambdaARN": None,
                    "RotationRules": {"AutomaticallyAfterDays": 0},
                    "Tags": [],
                }
            ],
        )
