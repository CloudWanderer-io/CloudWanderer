import pytest

from cloudwanderer.aws_interface import CloudWandererBoto3Session


@pytest.fixture
def cloudwanderer_boto3_session():
    return CloudWandererBoto3Session(aws_access_key_id="aaaa", aws_secret_access_key="aaaaaa")


@pytest.fixture
def s3_service(cloudwanderer_boto3_session):
    return cloudwanderer_boto3_session.resource("s3", region="us-east-1")


@pytest.fixture
def iam_service(cloudwanderer_boto3_session):
    return cloudwanderer_boto3_session.resource("iam")


@pytest.fixture
def ec2_service(cloudwanderer_boto3_session):
    return cloudwanderer_boto3_session.resource("ec2")
