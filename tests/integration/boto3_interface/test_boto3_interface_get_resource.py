import unittest
from unittest.mock import ANY

import boto3
import botocore

from cloudwanderer import AwsUrn, CloudWandererBoto3Interface
from cloudwanderer.exceptions import (
    BadRequest,
    BadUrnAccountId,
    BadUrnRegion,
    BadUrnSubResource,
    ResourceActionDoesNotExist,
    ResourceNotFound,
)

from ..helpers import DEFAULT_SESSION, GenericAssertionHelpers, get_default_mocker
from ..mocks import add_infra


class TestCloudWandererGetResource(unittest.TestCase, GenericAssertionHelpers):
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
        self.boto3_interface = CloudWandererBoto3Interface()

    def test_get_valid_ec2_instance(self):
        result = self.boto3_interface.get_resource(
            urn=AwsUrn(
                account_id="123456789012",
                region="eu-west-2",
                service="ec2",
                resource_type="instance",
                resource_id=self.instances[0].instance_id,
            )
        )

        assert set(self.instances[0].meta.data).issubset(result.cloudwanderer_metadata.resource_data)

    def test_get_valid_iam_role(self):
        result = self.boto3_interface.get_resource(
            urn=AwsUrn(
                account_id="123456789012",
                region="us-east-1",
                service="iam",
                resource_type="role",
                resource_id="test-role",
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

    def test_get_secondary_resource(self):
        with self.assertRaises(BadUrnSubResource):
            self.boto3_interface.get_resource(
                urn=AwsUrn(
                    account_id="123456789012",
                    region="us-east-1",
                    service="iam",
                    resource_type="role_policy",
                    resource_id="test-role/test-policy",
                )
            )

    def test_get_valid_s3_bucket_eu_west_2(self):
        result = self.boto3_interface.get_resource(
            urn=AwsUrn(
                account_id="123456789012",
                region="eu-west-2",
                service="s3",
                resource_type="bucket",
                resource_id="test-eu-west-2",
            )
        )
        assert result.cloudwanderer_metadata.resource_data == {
            "CreationDate": ANY,
            "Name": "test-eu-west-2",
        }

    def test_get_s3_bucket_bad_account_id(self):
        with self.assertRaises(BadUrnAccountId):
            self.boto3_interface.get_resource(
                urn=AwsUrn(
                    account_id="111111111111",
                    region="eu-west-2",
                    service="s3",
                    resource_type="bucket",
                    resource_id="test-eu-west-2",
                )
            )

    def test_get_invalid_iam_role_eu_west_2(self):
        with self.assertRaises(BadUrnRegion):
            self.boto3_interface.get_resource(
                urn=AwsUrn(
                    account_id="123456789012",
                    region="eu-west-2",
                    service="iam",
                    resource_type="role",
                    resource_id="test-role",
                )
            )

    def test_get_missing_ec2_instance_eu_west_2(self):
        with self.assertRaisesRegex(
            BadRequest,
            "A request error was returned while fetching urn:aws:123456789012:eu-west-2:ec2:instance:i-111111111111",
        ):
            self.boto3_interface.get_resource(
                urn=AwsUrn(
                    account_id="123456789012",
                    region="eu-west-2",
                    service="ec2",
                    resource_type="instance",
                    resource_id="i-111111111111",
                )
            )

    def test_get_missing_iam_role(self):
        with self.assertRaisesRegex(
            ResourceNotFound, "urn:aws:123456789012:us-east-1:iam:role:non-existent-role was not found"
        ):
            self.boto3_interface.get_resource(
                urn=AwsUrn(
                    account_id="123456789012",
                    region="us-east-1",
                    service="iam",
                    resource_type="role",
                    resource_id="non-existent-role",
                )
            )

    def test_get_custom_resource(self):
        result = self.boto3_interface.get_resource(
            urn=AwsUrn(
                account_id="123456789012",
                region="eu-west-2",
                service="secretsmanager",
                resource_type="secret",
                resource_id="test-secret",
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
            "RotationEnabled": False,
            "RotationLambdaARN": "",
            "RotationRules": {"AutomaticallyAfterDays": 0},
            "Tags": [],
            "VersionIdsToStages": ANY,
        }

    def test_get_invalid_service_resource(self):
        with self.assertRaisesRegex(botocore.exceptions.UnknownServiceError, "secretsmanag3r"):
            self.boto3_interface.get_resource(
                urn=AwsUrn(
                    account_id="123456789012",
                    region="eu-west-2",
                    service="secretsmanag3r",
                    resource_type="secret",
                    resource_id="test-secret",
                )
            )

    def test_get_invalid_type_resource(self):
        with self.assertRaisesRegex(
            ResourceActionDoesNotExist, "secr3t does not exist as a supported resource for secretsmanager"
        ):
            self.boto3_interface.get_resource(
                urn=AwsUrn(
                    account_id="123456789012",
                    region="eu-west-2",
                    service="secretsmanager",
                    resource_type="secr3t",
                    resource_id="test-secret",
                )
            )
