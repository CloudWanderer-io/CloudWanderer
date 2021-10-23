import pytest
from moto import mock_ec2, mock_iam

from cloudwanderer.aws_interface import CloudWandererBoto3Session

from .pytest_helpers import create_iam_role


@pytest.fixture
def cloudwanderer_boto3_session():
    return CloudWandererBoto3Session(aws_access_key_id="aaaa", aws_secret_access_key="aaaaaa")


@pytest.fixture
def s3_service(cloudwanderer_boto3_session):
    return cloudwanderer_boto3_session.resource("s3", region_name="us-east-1")


@pytest.fixture
def iam_service(cloudwanderer_boto3_session):
    return cloudwanderer_boto3_session.resource("iam", region_name="us-east-1")


@pytest.fixture
def ec2_service(cloudwanderer_boto3_session):
    return cloudwanderer_boto3_session.resource("ec2", region_name="eu-west-2")


@pytest.fixture
def single_iam_role(iam_service):
    """Return a single IAM Role.

    Be warned, you can ONLY access properties on the resultant role that do not entail additional API calls.
    Even if you add @mock_iam decorator to your test method the role will not exist in that context.

    To mock additional API calls use the @iam_service and @mock_iam fixtures on your test function and call
    create_iam_role within that.
    """
    with mock_iam():
        create_iam_role()
        return list(iam_service.collection("role").all())[0]


@pytest.fixture
def single_ec2_vpc(ec2_service):
    """Return a single Ec2 Vpc.

    Be warned, you can ONLY access properties on the resultant vpc that do not entail additional API calls.
    See single_iam_role for more details on how to mock additional API calls.
    """
    with mock_ec2():
        return list(ec2_service.collection("vpc").all())[0]
