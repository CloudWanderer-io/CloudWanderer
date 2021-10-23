from unittest.mock import ANY

import pytest
from moto import mock_ec2, mock_iam, mock_sts

from cloudwanderer import URN
from cloudwanderer.exceptions import UnsupportedResourceTypeError, UnsupportedServiceError
from tests.integration.pytest_helpers import compare_dict_allow_any

from ..pytest_helpers import create_iam_role


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
            "cloudwanderer_metadata": ANY,
            "dependent_resource_urns": [],
            "dhcp_options_id": ANY,
            "discovery_time": ANY,
            "enable_dns_support": True,
            "instance_tenancy": "default",
            "ipv6_cidr_block_association_set": [],
            "is_default": True,
            "owner_id": None,
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


# TODO: Add filter support back to get_resources
# def test_filters(self, mock_service: MagicMock):
#     aws_interface = CloudWandererAWSInterface(
#         resource_filters=[ResourceFilter(service_name="ec2", resource_type="image", filters={"Owners": "all"})]
#     )
#     list(aws_interface.get_resources(service_name="ec2", resource_type="image"))

#     mock_service.return_value.get_resources.assert_called_with(
#         resource_type="image", resource_filters={"Owners": "all"}
#     )
