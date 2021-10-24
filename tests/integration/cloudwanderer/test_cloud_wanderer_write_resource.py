from unittest.mock import ANY, patch

import boto3
from moto import mock_ec2, mock_iam, mock_s3, mock_secretsmanager, mock_sts

from cloudwanderer import URN

from ...pytest_helpers import compare_dict_allow_any, create_iam_role, create_s3_buckets, create_secretsmanager_secrets


@mock_ec2
@mock_sts
def test_write_valid_ec2_instance(cloudwanderer_aws):
    vpc = next(
        cloudwanderer_aws.cloud_interface.get_resources(service_name="ec2", resource_type="vpc", region="eu-west-2")
    )
    cloudwanderer_aws.write_resource(
        urn=URN(
            account_id="123456789012",
            region="eu-west-2",
            service="ec2",
            resource_type="vpc",
            resource_id_parts=[vpc.vpc_id],
        )
    )
    set(next((cloudwanderer_aws.storage_connectors[0].read_all()))).issubset(vpc.cloudwanderer_metadata.resource_data)


@mock_iam
@mock_sts
def test_write_valid_iam_role(cloudwanderer_aws):
    create_iam_role()
    cloudwanderer_aws.write_resource(
        urn=URN(
            account_id="123456789012",
            region="us-east-1",
            service="iam",
            resource_type="role",
            resource_id_parts=["test-role"],
        )
    )

    assert list(cloudwanderer_aws.storage_connectors[0].read_all()) == [
        {
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
            "attr": "BaseResource",
            "urn": "urn:aws:123456789012:us-east-1:iam:role_policy:test-role/test-role-policy",
        },
        {
            "attr": "ParentUrn",
            "urn": "urn:aws:123456789012:us-east-1:iam:role_policy:test-role/test-role-policy",
            "value": URN(
                account_id="123456789012",
                region="us-east-1",
                service="iam",
                resource_type="role",
                resource_id_parts=["test-role"],
            ),
        },
        {
            "attr": "DependentResourceUrns",
            "urn": "urn:aws:123456789012:us-east-1:iam:role_policy:test-role/test-role-policy",
            "value": [],
        },
        {
            "Arn": "arn:aws:iam::123456789012:role/test-role",
            "AssumeRolePolicyDocument": {},
            "CreateDate": ANY,
            "Description": None,
            "InlinePolicyAttachments": {"IsTruncated": False, "Marker": None, "PolicyNames": ["test-role-policy"]},
            "ManagedPolicyAttachments": {
                "AttachedPolicies": [
                    {
                        "PolicyArn": "arn:aws:iam::aws:policy/aws-service-role/APIGatewayServiceRolePolicy",
                        "PolicyName": "APIGatewayServiceRolePolicy",
                    }
                ],
                "IsTruncated": False,
                "Marker": None,
            },
            "MaxSessionDuration": 3600,
            "Path": "/",
            "PermissionsBoundary": None,
            "RoleId": ANY,
            "RoleLastUsed": None,
            "RoleName": "test-role",
            "Tags": None,
            "attr": "BaseResource",
            "urn": "urn:aws:123456789012:us-east-1:iam:role:test-role",
        },
        {"attr": "ParentUrn", "urn": "urn:aws:123456789012:us-east-1:iam:role:test-role", "value": None},
        {
            "attr": "DependentResourceUrns",
            "urn": "urn:aws:123456789012:us-east-1:iam:role:test-role",
            "value": [
                URN(
                    account_id="123456789012",
                    region="us-east-1",
                    service="iam",
                    resource_type="role_policy",
                    resource_id_parts=["test-role", "test-role-policy"],
                )
            ],
        },
    ]


@mock_s3
@mock_sts
def test_write_valid_s3_bucket_eu_west_2(cloudwanderer_aws):
    create_s3_buckets()

    cloudwanderer_aws.write_resource(
        urn=URN(
            account_id="123456789012",
            region="eu-west-2",
            service="s3",
            resource_type="bucket",
            resource_id_parts=["test-eu-west-2"],
        )
    )

    assert list(cloudwanderer_aws.storage_connectors[0].read_all()) == [
        {
            "CreationDate": ANY,
            "Name": "test-eu-west-2",
            "attr": "BaseResource",
            "urn": "urn:aws:123456789012:eu-west-2:s3:bucket:test-eu-west-2",
        },
        {"attr": "ParentUrn", "urn": "urn:aws:123456789012:eu-west-2:s3:bucket:test-eu-west-2", "value": None},
        {
            "attr": "DependentResourceUrns",
            "urn": "urn:aws:123456789012:eu-west-2:s3:bucket:test-eu-west-2",
            "value": [],
        },
    ]


@mock_ec2
@mock_sts
def test_write_non_existent_ec2_instance_eu_west_2(cloudwanderer_aws):
    with patch("cloudwanderer.storage_connectors.MemoryStorageConnector.delete_resource") as mock_delete_resource:
        cloudwanderer_aws.write_resource(
            urn=URN(
                account_id="123456789012",
                region="eu-west-2",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=["vpc-111111111"],
            )
        )

    mock_delete_resource.assert_called_with(
        URN(
            account_id="123456789012",
            region="eu-west-2",
            service="ec2",
            resource_type="vpc",
            resource_id_parts=["vpc-111111111"],
        )
    )


@mock_secretsmanager
@mock_sts
def test_write_custom_resource(cloudwanderer_aws):
    create_secretsmanager_secrets()

    cloudwanderer_aws.write_resource(
        urn=URN(
            account_id="123456789012",
            region="eu-west-2",
            service="secretsmanager",
            resource_type="secret",
            resource_id_parts=["TestSecret"],
        )
    )

    assert list(cloudwanderer_aws.storage_connectors[0].read_all()) == [
        {
            "ARN": ANY,
            "CreatedDate": None,
            "DeletedDate": None,
            "Description": None,
            "KmsKeyId": None,
            "LastAccessedDate": None,
            "LastChangedDate": None,
            "LastRotatedDate": None,
            "Name": "TestSecret",
            "OwningService": None,
            "PrimaryRegion": None,
            "ReplicationStatus": None,
            "RotationEnabled": False,
            "RotationLambdaARN": None,
            "RotationRules": {"AutomaticallyAfterDays": 0},
            "Tags": [],
            "VersionIdsToStages": ANY,
            "attr": "BaseResource",
            "urn": "urn:aws:123456789012:eu-west-2:secretsmanager:secret:TestSecret",
        },
        {
            "attr": "ParentUrn",
            "urn": "urn:aws:123456789012:eu-west-2:secretsmanager:secret:TestSecret",
            "value": None,
        },
        {
            "attr": "DependentResourceUrns",
            "urn": "urn:aws:123456789012:eu-west-2:secretsmanager:secret:TestSecret",
            "value": [],
        },
    ]


@mock_iam
@mock_sts
def test_cleanup_iam_role(cloudwanderer_aws):
    create_iam_role()
    role_urn = URN(
        account_id="123456789012",
        region="us-east-1",
        service="iam",
        resource_type="role",
        resource_id_parts=["test-role"],
    )
    role_keys = [
        {
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
            "attr": "BaseResource",
            "urn": "urn:aws:123456789012:us-east-1:iam:role_policy:test-role/test-role-policy",
        },
        {
            "attr": "ParentUrn",
            "urn": "urn:aws:123456789012:us-east-1:iam:role_policy:test-role/test-role-policy",
            "value": URN(
                cloud_name="aws",
                account_id="123456789012",
                region="us-east-1",
                service="iam",
                resource_type="role",
                resource_id_parts=["test-role"],
            ),
        },
        {
            "attr": "DependentResourceUrns",
            "urn": "urn:aws:123456789012:us-east-1:iam:role_policy:test-role/test-role-policy",
            "value": [],
        },
        {
            "Arn": "arn:aws:iam::123456789012:role/test-role",
            "AssumeRolePolicyDocument": {},
            "CreateDate": ANY,
            "Description": None,
            "InlinePolicyAttachments": {"IsTruncated": False, "Marker": None, "PolicyNames": ["test-role-policy"]},
            "ManagedPolicyAttachments": {
                "AttachedPolicies": [
                    {
                        "PolicyArn": "arn:aws:iam::aws:policy/aws-service-role/APIGatewayServiceRolePolicy",
                        "PolicyName": "APIGatewayServiceRolePolicy",
                    }
                ],
                "IsTruncated": False,
                "Marker": None,
            },
            "MaxSessionDuration": 3600,
            "Path": "/",
            "PermissionsBoundary": None,
            "RoleId": ANY,
            "RoleLastUsed": None,
            "RoleName": "test-role",
            "Tags": None,
            "attr": "BaseResource",
            "urn": "urn:aws:123456789012:us-east-1:iam:role:test-role",
        },
    ]

    # Initial discovery
    cloudwanderer_aws.write_resource(urn=role_urn)
    results = list(cloudwanderer_aws.storage_connectors[0].read_all())

    compare_dict_allow_any(role_keys[0], results[0])
    compare_dict_allow_any(role_keys[1], results[1])
    compare_dict_allow_any(role_keys[2], results[2])
    compare_dict_allow_any(role_keys[3], results[3])

    # Delete the role from AWS
    iam_resource = boto3.resource("iam")
    iam_resource.Role("test-role").detach_policy(
        PolicyArn="arn:aws:iam::aws:policy/aws-service-role/APIGatewayServiceRolePolicy"
    )
    iam_resource.Role("test-role").Policy("test-role-policy").delete()
    iam_resource.Role("test-role").delete()

    # Delete the role from storage
    cloudwanderer_aws.write_resource(urn=role_urn)
    assert list(cloudwanderer_aws.storage_connectors[0].read_all()) == []
