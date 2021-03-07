import unittest
from unittest.mock import ANY, patch

import boto3

from cloudwanderer import URN, CloudWanderer
from cloudwanderer.storage_connectors import MemoryStorageConnector

from ..helpers import DEFAULT_SESSION, get_default_mocker
from ..mocks import add_infra


class TestCloudWandererWriteResource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.enabled_regions = ["eu-west-2", "us-east-1", "ap-east-1"]
        mocker = get_default_mocker()
        mocker.start_moto_services(mocker.default_moto_services + ["mock_secretsmanager"])
        add_infra(regions=cls.enabled_regions)
        secretsmanager = boto3.client("secretsmanager")
        secretsmanager.create_secret(Name="test-secret", SecretString="Ssshhh")
        cls.instances = list(DEFAULT_SESSION.resource("ec2").instances.all())

    @classmethod
    def tearDownClass(cls):
        get_default_mocker().stop_general_mock()

    def setUp(self):
        self.storage_connector = MemoryStorageConnector()
        self.wanderer = CloudWanderer(storage_connectors=[self.storage_connector])

    def test_write_valid_ec2_instance(self):
        self.wanderer.write_resource(
            urn=URN(
                account_id="123456789012",
                region="eu-west-2",
                service="ec2",
                resource_type="instance",
                resource_id=self.instances[0].instance_id,
            )
        )
        set(next((self.storage_connector.read_all()))).issubset(self.instances[0].meta.data)

    def test_write_valid_iam_role(self):
        self.wanderer.write_resource(
            urn=URN(
                account_id="123456789012",
                region="us-east-1",
                service="iam",
                resource_type="role",
                resource_id="test-role",
            )
        )

        assert list(self.storage_connector.read_all()) == [
            {
                "Arn": "arn:aws:iam::123456789012:role/test-role",
                "AssumeRolePolicyDocument": {},
                "CreateDate": ANY,
                "Description": None,
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
            {
                "IsTruncated": False,
                "PolicyNames": ["test-role-policy"],
                "attr": "role_inline_policy_attachments",
                "urn": "urn:aws:123456789012:us-east-1:iam:role:test-role",
            },
            {
                "AttachedPolicies": [
                    {
                        "PolicyArn": "arn:aws:iam::aws:policy/aws-service-role/APIGatewayServiceRolePolicy",
                        "PolicyName": "APIGatewayServiceRolePolicy",
                    }
                ],
                "IsTruncated": False,
                "attr": "role_managed_policy_attachments",
                "urn": "urn:aws:123456789012:us-east-1:iam:role:test-role",
            },
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
                "IsTruncated": False,
                "PolicyNames": ["test-role-policy"],
                "attr": "role_inline_policy_attachments",
                "urn": "urn:aws:123456789012:us-east-1:iam:role_policy:test-role/test-role-policy",
            },
            {
                "AttachedPolicies": [
                    {
                        "PolicyArn": "arn:aws:iam::aws:policy/aws-service-role/APIGatewayServiceRolePolicy",
                        "PolicyName": "APIGatewayServiceRolePolicy",
                    }
                ],
                "IsTruncated": False,
                "attr": "role_managed_policy_attachments",
                "urn": "urn:aws:123456789012:us-east-1:iam:role_policy:test-role/test-role-policy",
            },
        ]

    def test_write_valid_s3_bucket_eu_west_2(self):
        self.wanderer.write_resource(
            urn=URN(
                account_id="123456789012",
                region="eu-west-2",
                service="s3",
                resource_type="bucket",
                resource_id="test-eu-west-2",
            )
        )
        assert list(self.storage_connector.read_all()) == [
            {
                "CreationDate": ANY,
                "Name": "test-eu-west-2",
                "attr": "BaseResource",
                "urn": "urn:aws:123456789012:eu-west-2:s3:bucket:test-eu-west-2",
            },
        ]

    @patch("cloudwanderer.storage_connectors.MemoryStorageConnector.delete_resource")
    def test_write_non_existent_ec2_instance_eu_west_2(self, mock_delete_resource):
        self.wanderer.write_resource(
            urn=URN(
                account_id="123456789012",
                region="eu-west-2",
                service="ec2",
                resource_type="instance",
                resource_id="i-11111111",
            )
        )

        mock_delete_resource.assert_called_with(
            URN(
                account_id="123456789012",
                region="eu-west-2",
                service="ec2",
                resource_type="instance",
                resource_id="i-11111111",
            )
        )

    def test_write_custom_resource(self):
        self.wanderer.write_resource(
            urn=URN(
                account_id="123456789012",
                region="eu-west-2",
                service="secretsmanager",
                resource_type="secret",
                resource_id="test-secret",
            )
        )

        assert list(self.storage_connector.read_all()) == [
            {
                "ARN": ANY,
                "CreatedDate": None,
                "DeletedDate": None,
                "Description": None,
                "KmsKeyId": None,
                "LastAccessedDate": None,
                "LastChangedDate": None,
                "LastRotatedDate": None,
                "Name": "test-secret",
                "OwningService": None,
                "PrimaryRegion": None,
                "ReplicationStatus": None,
                "RotationEnabled": False,
                "RotationLambdaARN": None,
                "RotationRules": {"AutomaticallyAfterDays": 0},
                "Tags": [],
                "VersionIdsToStages": ANY,
                "attr": "BaseResource",
                "urn": "urn:aws:123456789012:eu-west-2:secretsmanager:secret:test-secret",
            }
        ]
