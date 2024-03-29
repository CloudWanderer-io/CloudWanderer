import logging
from typing import List
from unittest.mock import MagicMock

import pytest
from moto import mock_ec2, mock_iam, mock_s3, mock_sts

from cloudwanderer import CloudWanderer
from cloudwanderer.aws_interface.interface import CloudWandererAWSInterface
from cloudwanderer.aws_interface.session import CloudWandererBoto3Session
from cloudwanderer.cloud_wanderer_resource import CloudWandererResource
from cloudwanderer.models import ServiceResourceType
from cloudwanderer.storage_connectors.memory import MemoryStorageConnector
from cloudwanderer.urn import URN

from ...helpers import assert_does_not_have_matching_urns, assert_has_matching_urns
from ...pytest_helpers import create_ec2_instances, create_iam_role, create_s3_buckets

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
@mock_ec2
@mock_iam
@mock_sts
@mock_s3
def loaded_memory_connector():
    create_iam_role()
    create_s3_buckets(regions=["us-east-1", "eu-west-2"])
    create_ec2_instances(regions=["us-east-1", "eu-west-2"])
    connector = MemoryStorageConnector()
    connector.init()
    wanderer = CloudWanderer(
        storage_connectors=[connector],
        cloud_interface=CloudWandererAWSInterface(
            cloudwanderer_boto3_session=CloudWandererBoto3Session(
                aws_access_key_id="aaaa", aws_secret_access_key="aaaaaa"
            )
        ),
    )
    for account_id in ["123456789012", "111111111111"]:
        wanderer.cloud_interface.cloudwanderer_boto3_session.get_account_id = MagicMock(return_value=account_id)
        wanderer.write_resources(
            regions=["us-east-1", "eu-west-2"],
            service_resource_types=[
                ServiceResourceType(service="ec2", resource_type="instance"),
                ServiceResourceType(service="ec2", resource_type="vpc"),
                ServiceResourceType(service="s3", resource_type="bucket"),
                ServiceResourceType(service="iam", resource_type="role"),
            ],
        )
    return connector


def test_no_args(loaded_memory_connector):

    result = list(loaded_memory_connector.read_resources())

    expected_urns = [
        {"account_id": "123456789012", "region": "eu-west-2", "service": "s3", "resource_type": "bucket"},
        {"account_id": "123456789012", "region": "us-east-1", "service": "s3", "resource_type": "bucket"},
        {"account_id": "123456789012", "region": "us-east-1", "service": "ec2", "resource_type": "vpc"},
        {"account_id": "123456789012", "region": "eu-west-2", "service": "ec2", "resource_type": "vpc"},
        {
            "account_id": "123456789012",
            "region": "us-east-1",
            "service": "iam",
            "resource_type": "role",
            "resource_id": "test-role",
        },
        {"account_id": "111111111111", "region": "eu-west-2", "service": "s3", "resource_type": "bucket"},
        {"account_id": "111111111111", "region": "us-east-1", "service": "s3", "resource_type": "bucket"},
        {"account_id": "111111111111", "region": "us-east-1", "service": "ec2", "resource_type": "vpc"},
        {"account_id": "111111111111", "region": "eu-west-2", "service": "ec2", "resource_type": "vpc"},
        {
            "account_id": "111111111111",
            "region": "us-east-1",
            "service": "iam",
            "resource_type": "role",
            "resource_id": "test-role",
        },
    ]
    not_expected_urns = []
    assert_has_matching_urns(result, expected_urns)
    assert_does_not_have_matching_urns(result, not_expected_urns)


def test_account_id(loaded_memory_connector):

    result: List[CloudWandererResource] = list(loaded_memory_connector.read_resources(account_id="123456789012"))

    expected_urns = [
        {"account_id": "123456789012", "region": "eu-west-2", "service": "s3", "resource_type": "bucket"},
        {"account_id": "123456789012", "region": "us-east-1", "service": "s3", "resource_type": "bucket"},
        {"account_id": "123456789012", "region": "us-east-1", "service": "ec2", "resource_type": "vpc"},
        {"account_id": "123456789012", "region": "eu-west-2", "service": "ec2", "resource_type": "vpc"},
        {
            "account_id": "123456789012",
            "region": "us-east-1",
            "service": "iam",
            "resource_type": "role",
            "resource_id": "test-role",
        },
    ]
    not_expected_urns = [
        {"account_id": "111111111111", "region": "eu-west-2", "service": "s3", "resource_type": "bucket"},
        {"account_id": "111111111111", "region": "us-east-1", "service": "s3", "resource_type": "bucket"},
        {"account_id": "111111111111", "region": "us-east-1", "service": "ec2", "resource_type": "vpc"},
        {"account_id": "111111111111", "region": "eu-west-2", "service": "ec2", "resource_type": "vpc"},
        {
            "account_id": "111111111111",
            "region": "us-east-1",
            "service": "iam",
            "resource_type": "role",
            "resource_id": "test-role",
        },
    ]
    assert_has_matching_urns(result, expected_urns)
    assert_does_not_have_matching_urns(result, not_expected_urns)


def test_region(loaded_memory_connector):
    result = list(loaded_memory_connector.read_resources(region="eu-west-2"))

    expected_urns = [
        {"account_id": "111111111111", "region": "eu-west-2", "service": "s3", "resource_type": "bucket"},
        {"account_id": "123456789012", "region": "eu-west-2", "service": "s3", "resource_type": "bucket"},
        {"account_id": "123456789012", "region": "eu-west-2", "service": "ec2", "resource_type": "vpc"},
        {"account_id": "111111111111", "region": "eu-west-2", "service": "ec2", "resource_type": "vpc"},
    ]
    not_expected_urns = [
        {"account_id": "123456789012", "region": "us-east-1", "service": "s3", "resource_type": "bucket"},
        {"account_id": "123456789012", "region": "us-east-1", "service": "ec2", "resource_type": "vpc"},
        {"account_id": "111111111111", "region": "us-east-1", "service": "s3", "resource_type": "bucket"},
        {"account_id": "111111111111", "region": "us-east-1", "service": "ec2", "resource_type": "vpc"},
        {
            "account_id": "111111111111",
            "region": "us-east-1",
            "service": "iam",
            "resource_type": "role",
            "resource_id": "test-role",
        },
    ]
    assert_has_matching_urns(result, expected_urns)
    assert_does_not_have_matching_urns(result, not_expected_urns)


def test_service(loaded_memory_connector):
    result = list(loaded_memory_connector.read_resources(service="ec2"))

    expected_urns = [
        {"account_id": "123456789012", "region": "eu-west-2", "service": "ec2", "resource_type": "vpc"},
        {"account_id": "111111111111", "region": "eu-west-2", "service": "ec2", "resource_type": "vpc"},
        {"account_id": "123456789012", "region": "us-east-1", "service": "ec2", "resource_type": "vpc"},
        {"account_id": "111111111111", "region": "us-east-1", "service": "ec2", "resource_type": "vpc"},
    ]
    not_expected_urns = [
        {"account_id": "111111111111", "region": "eu-west-2", "service": "s3", "resource_type": "bucket"},
        {"account_id": "123456789012", "region": "eu-west-2", "service": "s3", "resource_type": "bucket"},
        {"account_id": "123456789012", "region": "us-east-1", "service": "s3", "resource_type": "bucket"},
        {"account_id": "111111111111", "region": "us-east-1", "service": "s3", "resource_type": "bucket"},
        {
            "account_id": "111111111111",
            "region": "us-east-1",
            "service": "iam",
            "resource_type": "role",
            "resource_id": "test-role",
        },
    ]
    assert_has_matching_urns(result, expected_urns)
    assert_does_not_have_matching_urns(result, not_expected_urns)


def test_resource_type(loaded_memory_connector):
    result = list(loaded_memory_connector.read_resources(service="s3", resource_type="bucket"))

    expected_urns = [
        {"account_id": "123456789012", "region": "eu-west-2", "service": "s3", "resource_type": "bucket"},
        {"account_id": "123456789012", "region": "us-east-1", "service": "s3", "resource_type": "bucket"},
        {"account_id": "111111111111", "region": "eu-west-2", "service": "s3", "resource_type": "bucket"},
        {"account_id": "111111111111", "region": "us-east-1", "service": "s3", "resource_type": "bucket"},
    ]
    not_expected_urns = [
        {"account_id": "111111111111", "region": "us-east-1", "service": "ec2", "resource_type": "vpc"},
        {"account_id": "111111111111", "region": "eu-west-2", "service": "ec2", "resource_type": "vpc"},
        {
            "account_id": "111111111111",
            "region": "us-east-1",
            "service": "iam",
            "resource_type": "role",
            "resource_id": "test-role",
        },
        {"account_id": "123456789012", "region": "us-east-1", "service": "ec2", "resource_type": "vpc"},
        {"account_id": "123456789012", "region": "eu-west-2", "service": "ec2", "resource_type": "vpc"},
        {
            "account_id": "123456789012",
            "region": "us-east-1",
            "service": "iam",
            "resource_type": "role",
            "resource_id": "test-role",
        },
    ]
    assert_has_matching_urns(result, expected_urns)
    assert_does_not_have_matching_urns(result, not_expected_urns)


def test_resource_urn(loaded_memory_connector):

    result: List[CloudWandererResource] = list(
        loaded_memory_connector.read_resources(
            urn=URN(
                cloud_name="aws",
                account_id="111111111111",
                region="us-east-1",
                service="iam",
                resource_type="role",
                resource_id_parts=["test-role"],
            )
        )
    )

    expected_urns = [
        {
            "account_id": "111111111111",
            "region": "us-east-1",
            "service": "iam",
            "resource_type": "role",
            "resource_id": "test-role",
        },
    ]
    not_expected_urns = [
        {"account_id": "111111111111", "region": "us-east-1", "service": "ec2", "resource_type": "vpc"},
        {"account_id": "111111111111", "region": "eu-west-2", "service": "ec2", "resource_type": "vpc"},
        {"account_id": "123456789012", "region": "us-east-1", "service": "ec2", "resource_type": "vpc"},
        {"account_id": "123456789012", "region": "eu-west-2", "service": "ec2", "resource_type": "vpc"},
        {
            "account_id": "123456789012",
            "region": "us-east-1",
            "service": "iam",
            "resource_type": "role",
            "resource_id": "test-role",
        },
        {"account_id": "123456789012", "region": "eu-west-2", "service": "s3", "resource_type": "bucket"},
        {"account_id": "123456789012", "region": "us-east-1", "service": "s3", "resource_type": "bucket"},
        {"account_id": "111111111111", "region": "eu-west-2", "service": "s3", "resource_type": "bucket"},
        {"account_id": "111111111111", "region": "us-east-1", "service": "s3", "resource_type": "bucket"},
    ]
    assert_has_matching_urns(result, expected_urns)
    assert_does_not_have_matching_urns(result, not_expected_urns)


def test_dependent_resource_urn(loaded_memory_connector):
    result = next(
        loaded_memory_connector.read_resources(
            urn=URN(
                account_id="111111111111",
                region="us-east-1",
                service="iam",
                resource_type="role_policy",
                resource_id_parts=["test-role", "test-role-policy"],
            )
        ),
        None,
    )
    assert isinstance(result.parent_urn, URN)
    assert result.parent_urn == URN(
        account_id="111111111111",
        region="us-east-1",
        service="iam",
        resource_type="role",
        resource_id_parts=["test-role"],
    )
