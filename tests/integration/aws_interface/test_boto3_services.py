import unittest
from unittest.mock import patch

import cloudwanderer
from cloudwanderer.boto3_services import Boto3Services, CloudWandererBoto3Service
from cloudwanderer.urn import URN

from ..helpers import DEFAULT_SESSION, get_default_mocker


class TestBoto3Services(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        get_default_mocker().start_moto_services()
        cls.services = Boto3Services(boto3_session=DEFAULT_SESSION)

    @classmethod
    def tearDownClass(cls) -> None:
        get_default_mocker().stop_moto_services()

    def test_get_service_custom_service(self):
        service = self.services.get_service("lambda")

        assert isinstance(service, CloudWandererBoto3Service)

    def test_get_service_boto3_service(self):
        service = self.services.get_service("sqs")
        assert isinstance(service, CloudWandererBoto3Service)

    def test_get_service_boto3_combined_service(self):
        service = self.services.get_service("ec2")
        assert isinstance(service, CloudWandererBoto3Service)

    def test_get_service_boto3_unsupported_service(self):
        with self.assertRaises(cloudwanderer.exceptions.UnsupportedServiceError):
            self.services.get_service("not-a-real-service")

    def test_available_services(self):
        assert {
            "cloudformation",
            "glacier",
            "opsworks",
            "sqs",
            "dynamodb",
            "s3",
            "secretsmanager",
            "ec2",
            "iam",
            "sns",
            "apigateway",
            "cloudwatch",
            "lambda",
        }.issubset(set(self.services.available_services))

    @patch("cloudwanderer.boto3_services.Boto3Services.get_service")
    def test_get_resource_from_urn(self, mock_get_service):
        urn = URN.from_string("urn:aws:123456789012:eu-west-2:ec2:vpc:vpc-11111111")

        self.services.get_resource_from_urn(urn)

        mock_get_service.return_value.get_resource_from_urn.assert_called_with(urn)

    def test_get_resource_from_urn_bad_account_id(self):
        urn = URN.from_string("urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111")

        with self.assertRaises(cloudwanderer.exceptions.BadUrnAccountIdError):
            self.services.get_resource_from_urn(urn)

    def test_get_resource_from_urn_wrong_region_for_service(self):
        urn = URN.from_string("urn:aws:123456789012:eu-west-2:iam:role:test-role")

        with self.assertRaises(cloudwanderer.exceptions.BadUrnRegionError):
            self.services.get_resource_from_urn(urn)

    def test_get_resource_from_urn_subresource(self):
        urn = URN.from_string("urn:aws:123456789012:eu-west-2:iam:role_policy:test-role/test-policy")

        with self.assertRaises(cloudwanderer.exceptions.BadUrnSubResourceError):
            self.services.get_resource_from_urn(urn)

    def test_get_enabled_regions(self):
        for region in ["us-east-1", "ap-northeast-1", "eu-west-2"]:
            assert region in self.services.enabled_regions
