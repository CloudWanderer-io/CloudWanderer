from unittest.mock import ANY

from boto3.resources.base import ServiceResource
from moto import mock_ec2, mock_iam, mock_s3, mock_sts

from cloudwanderer.aws_interface.boto3_loaders import ResourceMap
from cloudwanderer.urn import URN

from ...pytest_helpers import compare_dict_allow_any, create_iam_role, create_s3_buckets


@mock_ec2
def test_raw_data(single_ec2_vpc):
    compare_dict_allow_any(
        {
            "CidrBlock": "172.31.0.0/16",
            "CidrBlockAssociationSet": [
                {
                    "AssociationId": ANY,
                    "CidrBlock": "172.31.0.0/16",
                    "CidrBlockState": {"State": "associated"},
                }
            ],
            "DhcpOptionsId": ANY,
            "InstanceTenancy": "default",
            "Ipv6CidrBlockAssociationSet": [],
            "IsDefault": True,
            "State": "available",
            "Tags": [],
            "VpcId": ANY,
        },
        single_ec2_vpc.meta.data,
        allow_partial_match_first=True,
    )


# TODO: There is a weird bug causing different versions of python to
# show OwnerId or not depending on the version. Needs further investigation.
# Worked around for now by omitting the key and using allow_partial_match=True
@mock_ec2
def test_normalized_raw_data(single_ec2_vpc):
    compare_dict_allow_any(
        {
            "CidrBlock": "172.31.0.0/16",
            "CidrBlockAssociationSet": [
                {
                    "AssociationId": ANY,
                    "CidrBlock": "172.31.0.0/16",
                    "CidrBlockState": {"State": "associated"},
                }
            ],
            "DhcpOptionsId": ANY,
            "InstanceTenancy": "default",
            "Ipv6CidrBlockAssociationSet": [],
            "IsDefault": True,
            "State": "available",
            "Tags": [],
            "VpcId": ANY,
        },
        single_ec2_vpc.normalized_raw_data,
        allow_partial_match_first=True,
    )


def test_resource_type(single_ec2_vpc):
    assert single_ec2_vpc.resource_type == "vpc"


def test_get_region_regional_resources(single_ec2_vpc):
    assert single_ec2_vpc.get_region() == "eu-west-2"


@mock_s3
def test_get_region_global_service_global_resources(s3_service):
    create_s3_buckets(regions=["us-east-1", "eu-west-2", "ap-east-1"])

    resource_regions = [resource.get_region() for resource in s3_service.collection("bucket").all()]

    assert sorted(resource_regions) == sorted(["us-east-1", "eu-west-2", "ap-east-1"])


@mock_sts
def test_get_account_id(single_ec2_vpc):
    assert single_ec2_vpc.get_account_id() == "123456789012"


def test_service_name(single_ec2_vpc):
    assert single_ec2_vpc.service_name == "ec2"


def test_resource_map(single_ec2_vpc):
    assert isinstance(single_ec2_vpc.resource_map, ResourceMap)


@mock_sts
def test_get_urn(single_ec2_vpc):
    assert isinstance(single_ec2_vpc.get_urn(), URN)
    assert str(single_ec2_vpc.get_urn()).startswith(
        "urn:aws:123456789012:eu-west-2:ec2:vpc"
    ), f"{single_ec2_vpc.get_urn()} does not match 'urn:aws:123456789012:eu-west-2:ec2:vpc'"


def test_dependent_resource_types(single_iam_role):
    assert "role_policy" in single_iam_role.dependent_resource_types


@mock_iam
@mock_sts
def test_collection(iam_service):
    create_iam_role()
    single_iam_role = list(iam_service.collection("role").all())[0]
    single_role_policy = list(single_iam_role.collection("role_policy").all())[0]
    single_role_policy.load()

    assert (
        str(single_role_policy.get_urn()) == "urn:aws:123456789012:us-east-1:iam:role_policy:test-role/test-role-policy"
    )
    assert single_role_policy.normalized_raw_data == {
        "PolicyDocument": {
            "Statement": {"Action": "s3:ListBucket", "Effect": "Allow", "Resource": "arn:aws:s3:::example_bucket"},
            "Version": "2012-10-17",
        },
        "PolicyName": "test-role-policy",
        "RoleName": "test-role",
    }


def test_secondary_attribute_names(single_ec2_vpc):
    assert single_ec2_vpc.secondary_attribute_names == ["vpc_enable_dns_support"]


@mock_iam
@mock_sts
def test_secondary_attribute_maps(iam_service):
    create_iam_role()
    single_iam_role = list(iam_service.collection("role").all())[0]
    assert single_iam_role.get_secondary_attributes_map() == {
        "InlinePolicyAttachments": {"PolicyNames": ["test-role-policy"], "IsTruncated": False, "Marker": None},
        "ManagedPolicyAttachments": {
            "AttachedPolicies": [
                {
                    "PolicyName": "APIGatewayServiceRolePolicy",
                    "PolicyArn": "arn:aws:iam::aws:policy/aws-service-role/APIGatewayServiceRolePolicy",
                }
            ],
            "IsTruncated": False,
            "Marker": None,
        },
    }


def test_shape(single_ec2_vpc):
    assert single_ec2_vpc.shape.name == "Vpc"


@mock_ec2
def test_relationships(ec2_service):
    single_ec2_vpc = list(ec2_service.collection("vpc").all())[0]
    assert single_ec2_vpc.relationships[0].partial_urn.resource_type == "dhcp_options"


def test_empty_resource(ec2_service):
    vpc = ec2_service.resource("vpc", empty_resource=True)

    assert isinstance(vpc, ServiceResource)


def test_empty_resource_is_dependent_resource_true(iam_service):
    assert iam_service.resource("role_policy", empty_resource=True).is_dependent_resource


def test_empty_resource_is_dependent_resource_false(iam_service):
    assert not iam_service.resource("role", empty_resource=True).is_dependent_resource
