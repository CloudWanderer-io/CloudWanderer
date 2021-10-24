from unittest.mock import MagicMock

from pytest import fixture
import botocore
from cloudwanderer.aws_interface import CloudWandererBoto3Session


@fixture
def botocore_session():
    botocore_session = botocore.session.Session()
    botocore_session.create_client = MagicMock(
        **{
            "return_value.get_caller_identity.return_value": {
                "UserId": "AIDASAMPLEUSERID",
                "Account": "111111111111",
                "Arn": "arn:aws:iam::111111111111:user/DevAdmin",
            },
            "return_value.describe_regions.return_value": {
                "Regions": [
                    {
                        "Endpoint": "ec2.eu-west-1.amazonaws.com",
                        "RegionName": "eu-west-1",
                        "OptInStatus": "opt-in-not-required",
                    }
                ]
            },
        }
    )
    return botocore_session


@fixture
def cloudwanderer_boto3_session(botocore_session):
    session = CloudWandererBoto3Session(botocore_session=botocore_session)
    return session


def test_account_id(cloudwanderer_boto3_session):
    assert cloudwanderer_boto3_session.get_account_id() == "111111111111"


def test_get_enabled_regions(cloudwanderer_boto3_session):
    assert cloudwanderer_boto3_session.get_enabled_regions() == ["eu-west-1"]
