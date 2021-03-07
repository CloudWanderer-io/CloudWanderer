import unittest
from unittest.mock import ANY

import boto3

from cloudwanderer import URN, CloudWandererAWSInterface
from cloudwanderer.exceptions import UnsupportedServiceError

from ..helpers import DEFAULT_SESSION, GenericAssertionHelpers, get_default_mocker
from ..mocks import add_infra


class TestBoto3InterfaceGetResource(unittest.TestCase, GenericAssertionHelpers):
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
        self.aws_interface = CloudWandererAWSInterface()

    def test_get_valid_ec2_instance(self):
        result = self.aws_interface.get_resource(
            urn=URN(
                account_id="123456789012",
                region="eu-west-2",
                service="ec2",
                resource_type="instance",
                resource_id=self.instances[0].instance_id,
            )
        )

        assert set(self.instances[0].meta.data).issubset(next(result).cloudwanderer_metadata.resource_data)

    def test_get_valid_iam_role(self):
        result = next(
            self.aws_interface.get_resource(
                urn=URN(
                    account_id="123456789012",
                    region="us-east-1",
                    service="iam",
                    resource_type="role",
                    resource_id="test-role",
                )
            )
        )

        assert result.cloudwanderer_metadata.resource_data == {
            "Arn": "arn:aws:iam::123456789012:role/test-role",
            "AssumeRolePolicyDocument": {},
            "CreateDate": ANY,
            "Description": None,
            "MaxSessionDuration": 3600,
            "Path": "/",
            "RoleId": ANY,
            "PermissionsBoundary": None,
            "RoleLastUsed": None,
            "RoleName": "test-role",
            "Tags": None,
        }
        assert result.cloudwanderer_metadata.secondary_attributes == [
            {"IsTruncated": False, "PolicyNames": ["test-role-policy"]},
            {
                "AttachedPolicies": [
                    {
                        "PolicyArn": "arn:aws:iam::aws:policy/aws-service-role/APIGatewayServiceRolePolicy",
                        "PolicyName": "APIGatewayServiceRolePolicy",
                    }
                ],
                "IsTruncated": False,
            },
        ]

    def test_get_valid_s3_bucket_eu_west_2(self):
        result = self.aws_interface.get_resource(
            urn=URN(
                account_id="123456789012",
                region="eu-west-2",
                service="s3",
                resource_type="bucket",
                resource_id="test-eu-west-2",
            )
        )
        assert next(result).cloudwanderer_metadata.resource_data == {
            "CreationDate": ANY,
            "Name": "test-eu-west-2",
        }

    def test_get_missing_ec2_instance_eu_west_2(self):
        result = next(
            self.aws_interface.get_resource(
                urn=URN(
                    account_id="123456789012",
                    region="eu-west-2",
                    service="ec2",
                    resource_type="instance",
                    resource_id="i-111111111111",
                )
            ),
            None,
        )

        assert result is None

    def test_get_missing_iam_role(self):
        result = next(
            self.aws_interface.get_resource(
                urn=URN(
                    account_id="123456789012",
                    region="us-east-1",
                    service="iam",
                    resource_type="role",
                    resource_id="non-existent-role",
                )
            ),
            None,
        )

        assert result is None

    def test_get_custom_resource(self):
        result = next(
            self.aws_interface.get_resource(
                urn=URN(
                    account_id="123456789012",
                    region="eu-west-2",
                    service="secretsmanager",
                    resource_type="secret",
                    resource_id="test-secret",
                )
            )
        )

        assert result.cloudwanderer_metadata.resource_data == {
            "ARN": ANY,
            "CreatedDate": None,
            "DeletedDate": None,
            "Description": "",
            "KmsKeyId": "",
            "LastAccessedDate": None,
            "LastChangedDate": None,
            "LastRotatedDate": None,
            "Name": "test-secret",
            "OwningService": None,
            "PrimaryRegion": None,
            "ReplicationStatus": None,
            "RotationEnabled": False,
            "RotationLambdaARN": "",
            "RotationRules": {"AutomaticallyAfterDays": 0},
            "Tags": [],
            "VersionIdsToStages": ANY,
        }

    def test_get_invalid_service_resource(self):
        with self.assertRaisesRegex(UnsupportedServiceError, "secretsmanag3r"):
            next(
                self.aws_interface.get_resource(
                    urn=URN(
                        account_id="123456789012",
                        region="eu-west-2",
                        service="secretsmanag3r",
                        resource_type="secret",
                        resource_id="test-secret",
                    )
                )
            )

    def test_get_resource_subresources(self):
        results = list(
            self.aws_interface.get_resource(
                urn=URN(
                    account_id="123456789012",
                    region="us-east-1",
                    service="iam",
                    resource_type="role",
                    resource_id="test-role",
                )
            )
        )

        assert results[1].cloudwanderer_metadata.resource_data == {
            "PolicyDocument": {
                "Statement": {"Action": "s3:ListBucket", "Effect": "Allow", "Resource": "arn:aws:s3:::example_bucket"},
                "Version": "2012-10-17",
            },
            "PolicyName": "test-role-policy",
            "RoleName": "test-role",
        }
