from unittest.mock import MagicMock

from cloudwanderer.aws_interface import CloudWandererBoto3ClientConfig, CloudWandererBoto3Session


def test_get_account_id_from_arg():
    botocore_session = MagicMock()
    subject = CloudWandererBoto3Session(botocore_session=botocore_session, account_id="0123456789012")

    assert subject.get_account_id() == "0123456789012"

    botocore_session.create_client.assert_not_called()


def test_get_account_id():
    botocore_session = MagicMock()
    subject = CloudWandererBoto3Session(
        botocore_session=botocore_session,
        getter_client_config=CloudWandererBoto3ClientConfig(sts={"endpoint_url": "sts.eu-west-1.amazonaws.com"}),
    )

    subject.get_account_id()

    botocore_session.create_client.assert_called_with(
        "sts",
        region_name=None,
        api_version=None,
        use_ssl=True,
        verify=None,
        endpoint_url="sts.eu-west-1.amazonaws.com",
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_session_token=None,
        config=None,
    )


def test_get_enabled_regions():
    botocore_session = MagicMock()
    subject = CloudWandererBoto3Session(
        botocore_session=botocore_session,
        getter_client_config=CloudWandererBoto3ClientConfig(ec2={"endpoint_url": "ec2.eu-west-1.amazonaws.com"}),
    )

    subject.get_enabled_regions()

    botocore_session.create_client.assert_called_with(
        "ec2",
        region_name=None,
        api_version=None,
        use_ssl=True,
        verify=None,
        endpoint_url="ec2.eu-west-1.amazonaws.com",
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_session_token=None,
        config=None,
    )


def test_get_enabled_regions_from_arg():
    botocore_session = MagicMock()
    subject = CloudWandererBoto3Session(botocore_session=botocore_session, enabled_regions=["eu-west-1"])

    assert subject.get_enabled_regions() == ["eu-west-1"]

    botocore_session.create_client.assert_not_called()
