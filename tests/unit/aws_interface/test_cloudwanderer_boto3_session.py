from unittest.mock import MagicMock

from cloudwanderer.aws_interface import CloudWandererBoto3Session, CloudWandererBoto3SessionGetterClientConfig


def test_get_account_id():
    botocore_session = MagicMock()
    subject = CloudWandererBoto3Session(
        aws_access_key_id="A",
        aws_secret_access_key="A",
        aws_session_token="A",
        botocore_session=botocore_session,
        getter_client_config=CloudWandererBoto3SessionGetterClientConfig(
            sts={"endpoint_url": "sts.eu-west-1.amazonaws.com"}
        ),
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
        aws_access_key_id="A",
        aws_secret_access_key="A",
        aws_session_token="A",
        botocore_session=botocore_session,
        getter_client_config=CloudWandererBoto3SessionGetterClientConfig(
            ec2={"endpoint_url": "ec2.eu-west-1.amazonaws.com"}
        ),
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
