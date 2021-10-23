import unittest

from boto3.resources.base import ServiceResource

import cloudwanderer
from cloudwanderer.aws_interface import CloudWandererBoto3Session

from ..helpers import get_default_mocker


class TestBoto3Services(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        get_default_mocker().start_moto_services()
        cls.session = CloudWandererBoto3Session(aws_access_key_id="")

    @classmethod
    def tearDownClass(cls) -> None:
        get_default_mocker().stop_moto_services()

    def test_get_service_custom_service(self):
        service = self.services.resource("lambda")

        assert isinstance(service, ServiceResource)

    def test_get_service_boto3_service(self):
        service = self.services.resource("sqs")
        assert isinstance(service, ServiceResource)

    def test_get_service_boto3_combined_service(self):
        service = self.services.get_service("ec2")
        assert isinstance(service, ServiceResource)

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
        }.issubset(set(self.services.get_available_services()))

    def test_get_enabled_regions(self):
        for region in ["us-east-1", "ap-northeast-1", "eu-west-2"]:
            assert region in self.services.enabled_regions


def test_account_id(ec2_service):
    assert ec2_service.account_id == "123456789012"


def test_get_enabled_regions(self):
    assert self.service.enabled_regions == [
        "us-east-1",
        "ap-east-1",
        "eu-west-2",
    ]
