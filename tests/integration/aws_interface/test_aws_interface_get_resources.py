from unittest.mock import ANY

import pytest
from moto import mock_ec2, mock_iam, mock_sts
from itertools import islice
from cloudwanderer import URN
from cloudwanderer.aws_interface.models import AWSResourceTypeFilter
from cloudwanderer.exceptions import UnsupportedResourceTypeError, UnsupportedServiceError

from ...pytest_helpers import compare_dict_allow_any, create_iam_policy, create_iam_role


@mock_ec2
@mock_sts
def test_get_resources_of_type_in_region_eu_west_2(aws_interface):
    result = list(
        aws_interface.get_resources(
            service_name="ec2",
            resource_type="vpc",
            region="eu-west-2",
        )
    )[0]

    compare_dict_allow_any(
        dict(result),
        {
            "cidr_block": "172.31.0.0/16",
            "cidr_block_association_set": ANY,
            "cloudwanderer_metadata": {
                "CidrBlock": "172.31.0.0/16",
                "CidrBlockAssociationSet": [
                    {
                        "AssociationId": ANY,
                        "CidrBlock": "172.31.0.0/16",
                        "CidrBlockState": {"State": "associated"},
                    }
                ],
                "DhcpOptionsId": ANY,
                "EnableDnsSupport": True,
                "InstanceTenancy": "default",
                "Ipv6CidrBlockAssociationSet": [],
                "IsDefault": True,
                "OwnerId": ANY,
                "State": "available",
                "Tags": [],
                "VpcId": ANY,
            },
            "dependent_resource_urns": [],
            "dhcp_options_id": ANY,
            "discovery_time": ANY,
            "enable_dns_support": True,
            "instance_tenancy": "default",
            "ipv6_cidr_block_association_set": [],
            "is_default": True,
            "owner_id": ANY,
            "parent_urn": None,
            "relationships": ANY,
            "state": "available",
            "tags": [],
            "urn": ANY,
            "vpc_id": ANY,
        },
    )


@mock_iam
@mock_sts
def test_get_resources_of_type_in_region_us_east_1(aws_interface):
    create_iam_role()
    result = list(aws_interface.get_resources(service_name="iam", resource_type="role", region="us-east-1"))[0]

    compare_dict_allow_any(
        dict(result),
        {
            "urn": URN(
                cloud_name="aws",
                account_id="123456789012",
                region="us-east-1",
                service="iam",
                resource_type="role_policy",
                resource_id_parts=["test-role", "test-role-policy"],
            ),
            "relationships": [],
            "dependent_resource_urns": [],
            "parent_urn": URN(
                cloud_name="aws",
                account_id="123456789012",
                region="us-east-1",
                service="iam",
                resource_type="role",
                resource_id_parts=["test-role"],
            ),
            "cloudwanderer_metadata": {
                "RoleName": "test-role",
                "PolicyName": "test-role-policy",
                "PolicyDocument": {
                    "Version": "2012-10-17",
                    "Statement": {
                        "Effect": "Allow",
                        "Action": "s3:ListBucket",
                        "Resource": "arn:aws:s3:::example_bucket",
                    },
                },
            },
            "discovery_time": ANY,
            "role_name": "test-role",
            "policy_name": "test-role-policy",
            "policy_document": {
                "Version": "2012-10-17",
                "Statement": {"Effect": "Allow", "Action": "s3:ListBucket", "Resource": "arn:aws:s3:::example_bucket"},
            },
        },
    )


def test_get_resources_unsupported_service(aws_interface):
    with pytest.raises(UnsupportedServiceError):
        list(aws_interface.get_resources(service_name="unicorn_stable", resource_type="instance", region="eu-west-1"))


def test_get_resources_unsupported_resource_type(aws_interface):
    with pytest.raises(
        UnsupportedResourceTypeError,
        match="Could not find Boto3 collection for unicorn",
    ):
        list(aws_interface.get_resources(service_name="ec2", resource_type="unicorn", region="eu-west-1"))


@mock_iam
@mock_sts
def test_jmespath_filters(aws_interface):
    create_iam_policy()
    result = aws_interface.get_resources(
        service_name="iam",
        resource_type="policy",
        region="us-east-1",
        service_resource_type_filters=[
            AWSResourceTypeFilter(
                service="iam", resource_type="policy_version", jmespath_filters=["[?IsDefaultVersion==`true`]"]
            )
        ],
    )

    assert list(islice((r.is_default_version for r in result if hasattr(r, "is_default_version")), 10)) == [True] * 10


# TODO: test custom and default filters
