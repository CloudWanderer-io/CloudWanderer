import unittest

from cloudwanderer.aws_interface.boto3_loaders import MergedServiceLoader


class TestMergedServiceLoader(unittest.TestCase):
    def setUp(self) -> None:
        self.loader = MergedServiceLoader()

    def test_available_services(self):
        assert {
            "iam",
            "lambda",
            "apigateway",
            "dynamodb",
            "opsworks",
            "ec2",
            "sns",
            "s3",
            "cloudformation",
            "cloudwatch",
            "secretsmanager",
            "sqs",
            "glacier",
        }.issubset(self.loader.available_services)

    def test_get_service_definition(self):
        result = self.loader.get_service_definition("ec2")

        assert "resources" in result
        assert "service" in result

    def test_cloudwanderer_available_services(self):
        assert {"iam", "secretsmanager", "apigateway", "ec2", "lambda"}.issubset(
            self.loader.cloudwanderer_available_services
        )

    def test_boto3_available_services(self):
        assert {
            "cloudformation",
            "cloudwatch",
            "dynamodb",
            "ec2",
            "glacier",
            "iam",
            "opsworks",
            "s3",
            "sns",
            "sqs",
        }.issubset(self.loader.boto3_available_services)
