from unittest.mock import ANY

import pytest
from moto import mock_ec2, mock_iam, mock_s3, mock_secretsmanager, mock_sts

from cloudwanderer import URN
from cloudwanderer.exceptions import UnsupportedServiceError

from ..pytest_helpers import compare_dict_allow_any, create_iam_role, create_s3_buckets, create_secretsmanager_secrets


@mock_ec2
@mock_sts
def test_get_valid_ec2_vpc(aws_interface):
    vpc = next(aws_interface.get_resources(service_name="ec2", resource_type="vpc", region="eu-west-2"))

    result = next(
        aws_interface.get_resource(
            urn=URN(
                account_id="123456789012",
                region="eu-west-2",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=[vpc.vpc_id],
            )
        )
    )

    compare_dict_allow_any(
        dict(result),
        {
            "urn": ANY,
            "relationships": ANY,
            "dependent_resource_urns": [],
            "parent_urn": None,
            "cloudwanderer_metadata": {
                "CidrBlock": "172.31.0.0/16",
                "DhcpOptionsId": ANY,
                "State": "available",
                "VpcId": ANY,
                "OwnerId": None,
                "InstanceTenancy": "default",
                "Ipv6CidrBlockAssociationSet": [],
                "CidrBlockAssociationSet": [
                    {
                        "AssociationId": ANY,
                        "CidrBlock": "172.31.0.0/16",
                        "CidrBlockState": {"State": "associated"},
                    }
                ],
                "IsDefault": True,
                "Tags": [],
                "EnableDnsSupport": True,
            },
            "discovery_time": ANY,
            "cidr_block": "172.31.0.0/16",
            "dhcp_options_id": ANY,
            "state": "available",
            "vpc_id": ANY,
            "owner_id": None,
            "instance_tenancy": "default",
            "ipv6_cidr_block_association_set": [],
            "cidr_block_association_set": [
                {
                    "AssociationId": ANY,
                    "CidrBlock": "172.31.0.0/16",
                    "CidrBlockState": {"State": "associated"},
                }
            ],
            "is_default": True,
            "tags": [],
            "enable_dns_support": True,
        },
    )


@mock_iam
@mock_sts
def test_get_valid_iam_role(aws_interface):
    create_iam_role()
    result = next(
        aws_interface.get_resource(
            urn=URN(
                account_id="123456789012",
                region="us-east-1",
                service="iam",
                resource_type="role",
                resource_id_parts=["test-role"],
            )
        )
    )

    compare_dict_allow_any(
        dict(result),
        {
            "cloudwanderer_metadata": {
                "PolicyDocument": {
                    "Statement": {
                        "Action": "s3:ListBucket",
                        "Effect": "Allow",
                        "Resource": "arn:aws:s3:::example_bucket",
                    },
                    "Version": "2012-10-17",
                },
                "PolicyName": "test-role-policy",
                "RoleName": "test-role",
            },
            "dependent_resource_urns": [],
            "discovery_time": ANY,
            "parent_urn": URN(
                cloud_name="aws",
                account_id="123456789012",
                region="us-east-1",
                service="iam",
                resource_type="role",
                resource_id_parts=["test-role"],
            ),
            "policy_document": {
                "Statement": {
                    "Action": "s3:ListBucket",
                    "Effect": "Allow",
                    "Resource": "arn:aws:s3:::example_bucket",
                },
                "Version": "2012-10-17",
            },
            "policy_name": "test-role-policy",
            "relationships": [],
            "role_name": "test-role",
            "urn": URN(
                cloud_name="aws",
                account_id="123456789012",
                region="us-east-1",
                service="iam",
                resource_type="role_policy",
                resource_id_parts=["test-role", "test-role-policy"],
            ),
        },
    )


@mock_s3
@mock_sts
def test_get_valid_s3_bucket_eu_west_2(aws_interface):
    create_s3_buckets(regions=["eu-west-2"])
    result = next(
        aws_interface.get_resource(
            urn=URN(
                account_id="123456789012",
                region="eu-west-2",
                service="s3",
                resource_type="bucket",
                resource_id_parts=["test-eu-west-2"],
            )
        )
    )

    compare_dict_allow_any(
        dict(result),
        {
            "cloudwanderer_metadata": {
                "CreationDate": ANY,
                "Name": "test-eu-west-2",
            },
            "creation_date": ANY,
            "dependent_resource_urns": [],
            "discovery_time": ANY,
            "name": "test-eu-west-2",
            "parent_urn": None,
            "relationships": [],
            "urn": URN(
                cloud_name="aws",
                account_id="123456789012",
                region="eu-west-2",
                service="s3",
                resource_type="bucket",
                resource_id_parts=["test-eu-west-2"],
            ),
        },
    )


@mock_ec2
def test_get_missing_ec2_instance_eu_west_2(aws_interface):
    result = next(
        aws_interface.get_resource(
            urn=URN(
                account_id="123456789012",
                region="eu-west-2",
                service="ec2",
                resource_type="instance",
                resource_id_parts=["i-111111111111"],
            )
        ),
        None,
    )

    assert result is None


@mock_iam
def test_get_missing_iam_role(aws_interface):
    result = next(
        aws_interface.get_resource(
            urn=URN(
                account_id="123456789012",
                region="us-east-1",
                service="iam",
                resource_type="role",
                resource_id_parts=["non-existent-role"],
            )
        ),
        None,
    )

    assert result is None


@mock_secretsmanager
@mock_sts
def test_get_custom_resource(aws_interface):
    create_secretsmanager_secrets()
    result = next(
        aws_interface.get_resource(
            urn=URN(
                account_id="123456789012",
                region="eu-west-2",
                service="secretsmanager",
                resource_type="secret",
                resource_id_parts=["TestSecret"],
            )
        )
    )

    compare_dict_allow_any(
        dict(result),
        {
            "arn": ANY,
            "cloudwanderer_metadata": {
                "ARN": ANY,
                "CreatedDate": None,
                "DeletedDate": None,
                "Description": "",
                "KmsKeyId": "",
                "LastAccessedDate": None,
                "LastChangedDate": None,
                "LastRotatedDate": None,
                "Name": "TestSecret",
                "OwningService": None,
                "PrimaryRegion": None,
                "ReplicationStatus": None,
                "RotationEnabled": False,
                "RotationLambdaARN": "",
                "RotationRules": {"AutomaticallyAfterDays": 0},
                "Tags": [],
                "VersionIdsToStages": ANY,
            },
            "created_date": None,
            "deleted_date": None,
            "dependent_resource_urns": [],
            "description": "",
            "discovery_time": ANY,
            "kms_key_id": "",
            "last_accessed_date": None,
            "last_changed_date": None,
            "last_rotated_date": None,
            "name": "TestSecret",
            "owning_service": None,
            "parent_urn": None,
            "primary_region": None,
            "relationships": [],
            "replication_status": None,
            "rotation_enabled": False,
            "rotation_lambda_arn": "",
            "rotation_rules": {"AutomaticallyAfterDays": 0},
            "tags": [],
            "urn": URN(
                cloud_name="aws",
                account_id="123456789012",
                region="eu-west-2",
                service="secretsmanager",
                resource_type="secret",
                resource_id_parts=["TestSecret"],
            ),
            "version_ids_to_stages": ANY,
        },
    )


def test_get_invalid_service_resource(aws_interface):
    with pytest.raises(UnsupportedServiceError, match="secretsmanag3r"):
        next(
            aws_interface.get_resource(
                urn=URN(
                    account_id="123456789012",
                    region="eu-west-2",
                    service="secretsmanag3r",
                    resource_type="secret",
                    resource_id_parts=["test-secret"],
                )
            )
        )


@mock_iam
@mock_sts
def test_get_resource_subresources(aws_interface):
    create_iam_role()
    result = next(
        aws_interface.get_resource(
            urn=URN(
                account_id="123456789012",
                region="us-east-1",
                service="iam",
                resource_type="role",
                resource_id_parts=["test-role"],
            )
        )
    )

    assert result.cloudwanderer_metadata.resource_data == {
        "PolicyDocument": {
            "Statement": {"Action": "s3:ListBucket", "Effect": "Allow", "Resource": "arn:aws:s3:::example_bucket"},
            "Version": "2012-10-17",
        },
        "PolicyName": "test-role-policy",
        "RoleName": "test-role",
    }


@mock_iam
@mock_sts
def test_get_subresource(aws_interface):
    create_iam_role()
    result = next(
        aws_interface.get_resource(
            urn=URN(
                account_id="123456789012",
                region="us-east-1",
                service="iam",
                resource_type="role_policy",
                resource_id_parts=["test-role", "test-role-policy"],
            )
        )
    )

    assert result.cloudwanderer_metadata.resource_data == {
        "PolicyDocument": {
            "Statement": {
                "Action": "s3:ListBucket",
                "Effect": "Allow",
                "Resource": "arn:aws:s3:::example_bucket",
            },
            "Version": "2012-10-17",
        },
        "PolicyName": "test-role-policy",
        "RoleName": "test-role",
    }
