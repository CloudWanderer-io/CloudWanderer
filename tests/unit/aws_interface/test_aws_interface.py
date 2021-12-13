from unittest.mock import MagicMock

from cloudwanderer.aws_interface import CloudWandererAWSInterface


def test_get_account_id():
    subject = CloudWandererAWSInterface(
        cloudwanderer_boto3_session=MagicMock(**{"get_account_id.return_value": "0123456789012"})
    )

    assert subject.get_account_id() == "0123456789012"


def test_get_account_id_init_arg():
    subject = CloudWandererAWSInterface(account_id="0123456789012")

    assert subject.get_account_id() == "0123456789012"


def test_get_enabled_regions():
    subject = CloudWandererAWSInterface(
        cloudwanderer_boto3_session=MagicMock(**{"get_enabled_regions.return_value": ["eu-west-1"]})
    )

    assert subject.get_enabled_regions() == ["eu-west-1"]


def test_get_enabled_regions_init_arg():
    subject = CloudWandererAWSInterface(enabled_regions=["eu-west-1"])

    assert subject.get_enabled_regions() == ["eu-west-1"]
