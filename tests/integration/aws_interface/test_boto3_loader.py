import pytest

from cloudwanderer.aws_interface.boto3_loaders import MergedServiceLoader


@pytest.fixture
def merged_service_loader():
    return MergedServiceLoader()


def test_available_services(merged_service_loader):
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
    }.issubset(merged_service_loader.list_available_services())


def test_load_service_model(merged_service_loader):
    result = merged_service_loader.load_service_model("ec2", "resources-1")

    assert "resources" in result
    assert "service" in result


def test_cloudwanderer_available_services(merged_service_loader):
    assert {"iam", "secretsmanager", "apigateway", "ec2", "lambda"}.issubset(
        merged_service_loader.cloudwanderer_available_services
    )


def test_boto3_available_services(merged_service_loader):
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
    }.issubset(merged_service_loader.boto3_available_services)


def test_list_api_versions(merged_service_loader):
    assert "2016-11-15" in merged_service_loader.list_api_versions("ec2", "resources-1")


def test_determine_latest_version(merged_service_loader):
    assert merged_service_loader.determine_latest_version("ec2", "resources-1") == "2016-11-15"
