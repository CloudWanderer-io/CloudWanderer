import pytest
from boto3.resources.base import ServiceResource
from moto import mock_ec2, mock_sts

import cloudwanderer


def test_get_service_custom_service(cloudwanderer_boto3_session):
    service = cloudwanderer_boto3_session.resource("lambda")

    assert isinstance(service, ServiceResource)


def test_get_service_boto3_service(cloudwanderer_boto3_session):
    service = cloudwanderer_boto3_session.resource("sqs")
    assert isinstance(service, ServiceResource)


def test_get_service_boto3_combined_service(cloudwanderer_boto3_session):
    service = cloudwanderer_boto3_session.resource("ec2")
    assert isinstance(service, ServiceResource)


def test_get_service_boto3_unsupported_service(cloudwanderer_boto3_session):
    with pytest.raises(cloudwanderer.exceptions.UnsupportedServiceError):
        cloudwanderer_boto3_session.resource("not-a-real-service")


def test_available_services(cloudwanderer_boto3_session):
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
    }.issubset(set(cloudwanderer_boto3_session.get_available_services()))


@mock_ec2
def test_get_enabled_regions(cloudwanderer_boto3_session):
    for region in ["us-east-1", "ap-northeast-1", "eu-west-2"]:
        assert region in cloudwanderer_boto3_session.get_enabled_regions()


@mock_sts
def test_account_id(cloudwanderer_boto3_session):
    assert cloudwanderer_boto3_session.get_account_id() == "123456789012"
