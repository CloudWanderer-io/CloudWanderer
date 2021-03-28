import unittest
from unittest.mock import ANY, patch

import cloudwanderer
from cloudwanderer.boto3_services import (
    Boto3Services,
    CloudWandererBoto3Resource,
    CloudWandererBoto3Service,
    ResourceSummary,
)
from cloudwanderer.cloud_wanderer_resource import SecondaryAttribute
from cloudwanderer.models import CleanupAction, GetAction, GetAndCleanUp
from cloudwanderer.urn import URN

from ..helpers import DEFAULT_SESSION, get_default_mocker
from ..mocks import add_infra


class TestBoto3Services(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        get_default_mocker().start_moto_services()
        cls.services = Boto3Services(boto3_session=DEFAULT_SESSION)

    @classmethod
    def tearDownClass(cls) -> None:
        get_default_mocker().stop_moto_services()

    def test_get_service_custom_service(self):
        service = self.services.get_service("lambda")

        assert isinstance(service, CloudWandererBoto3Service)

    def test_get_service_boto3_service(self):
        service = self.services.get_service("sqs")
        assert isinstance(service, CloudWandererBoto3Service)

    def test_get_service_boto3_combined_service(self):
        service = self.services.get_service("ec2")
        assert isinstance(service, CloudWandererBoto3Service)

    def test_get_service_boto3_unsupported_service(self):
        with self.assertRaises(cloudwanderer.exceptions.UnsupportedServiceError):
            self.services.get_service("not-a-real-service")

    def test_available_services(self):
        assert {
            "cloudformation",
            "glacier",
            "opsworks",
            "sqs",
            "dynamodb",
            "s3",
            "secretsmanager",
            "ec2",
            "iam",
            "sns",
            "apigateway",
            "cloudwatch",
            "lambda",
        }.issubset(set(self.services.available_services))

    @patch("cloudwanderer.boto3_services.Boto3Services.get_service")
    def test_get_resource_from_urn(self, mock_get_service):
        urn = URN.from_string("urn:aws:123456789012:eu-west-2:ec2:vpc:vpc-11111111")

        self.services.get_resource_from_urn(urn)

        mock_get_service.return_value.get_resource_from_urn.assert_called_with(urn)

    def test_get_resource_from_urn_bad_account_id(self):
        urn = URN.from_string("urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111")

        with self.assertRaises(cloudwanderer.exceptions.BadUrnAccountIdError):
            self.services.get_resource_from_urn(urn)

    def test_get_resource_from_urn_wrong_region_for_service(self):
        urn = URN.from_string("urn:aws:123456789012:eu-west-2:iam:role:test-role")

        with self.assertRaises(cloudwanderer.exceptions.BadUrnRegionError):
            self.services.get_resource_from_urn(urn)

    def test_get_resource_from_urn_subresource(self):
        urn = URN.from_string("urn:aws:123456789012:eu-west-2:iam:role_policy:test-role/test-policy")

        with self.assertRaises(cloudwanderer.exceptions.BadUrnSubResourceError):
            self.services.get_resource_from_urn(urn)

    def test_get_enabled_regions(self):
        for region in ["us-east-1", "ap-northeast-1", "eu-west-2"]:
            assert region in self.services.enabled_regions


class TestCloudWandererBoto3Service(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        get_default_mocker().start_general_mock(restrict_regions=["us-east-1", "ap-east-1", "eu-west-2"])
        add_infra()
        cls.services = Boto3Services(boto3_session=DEFAULT_SESSION)
        cls.service = cls.services.get_service("ec2")
        cls.s3_service = cls.services.get_service("s3", region_name="us-east-1")
        cls.iam_service = cls.services.get_service("iam", region_name="us-east-1")
        cls.iam_service_wrong_region = cls.services.get_service("iam", region_name="eu-west-2")

    @classmethod
    def tearDownClass(cls) -> None:
        get_default_mocker().stop_general_mock()

    def test_resource_types(self):
        assert {"instance", "internet_gateway", "key_pair"}.issubset(set(self.service.resource_types))

    def test_get_resources(self):
        assert isinstance(next(self.service.get_resources("vpc")), CloudWandererBoto3Resource)

    def test_get_resources_from_urn(self):
        vpc = next(self.service.get_resources("vpc"))
        assert isinstance(self.service.get_resource_from_urn(vpc.urn), CloudWandererBoto3Resource)

    def test_get_global_endpoint_resources_in_regional_resource_region(self):
        service = self.services.get_service("s3", region_name="eu-west-2")
        resource_regions = list(resource.region for resource in service.get_resources("bucket"))

        assert sorted(resource_regions) == sorted(["us-east-1", "eu-west-2", "ap-east-1"])

    def test_region_default(self):
        assert self.service.region == "eu-west-2"

    def test_region_global_service_defined(self):
        assert self.iam_service.region == "us-east-1"

    def test_region_global_service_undefined(self):
        iam_service = self.services.get_service("iam")
        assert iam_service.region == "us-east-1"

    def test_should_query_resources_in_region_regional_service(self):
        assert self.service.should_query_resources_in_region

    def test_should_query_resources_in_region_global_service_regional_resources(self):
        assert self.s3_service.should_query_resources_in_region

    def test_should_query_resources_in_region_global_service_regional_resources_wrong_query_region(self):
        s3_service = self.services.get_service("s3", region_name="eu-west-2")
        assert not s3_service.should_query_resources_in_region

    def test_should_query_resources_in_region_global_service_global_resources(self):
        assert self.iam_service.should_query_resources_in_region

    def test_get_regions_discovered_from_region_regional_service(self):
        assert self.service.get_regions_discovered_from_region == ["eu-west-2"]

    def test_get_regions_discovered_from_region_global_service_regional_resources(self):
        assert sorted(self.s3_service.get_regions_discovered_from_region) == sorted(
            ["us-east-1", "eu-west-2", "ap-east-1"]
        )

    def test_get_regions_discovered_from_region_global_service_regional_resources_wrong_region(self):
        s3_service = self.services.get_service("s3", region_name="eu-west-2")

        assert s3_service.get_regions_discovered_from_region == []

    def test_get_regions_discovered_from_region_global_service_global_resources(self):
        assert self.iam_service.get_regions_discovered_from_region == ["us-east-1"]

    def test_get_regions_discovered_from_region_global_service_global_resources_wrong_region(self):
        assert self.iam_service_wrong_region.get_regions_discovered_from_region == []

    def test_account_id(self):
        assert self.service.account_id == "123456789012"

    def test_resource_summary(self):
        assert (
            ResourceSummary(
                resource_type="vpc", subresource_types=[], secondary_attribute_names=["vpc_enable_dns_support"]
            )
            in self.service.resource_summary
        )
        assert (
            ResourceSummary(
                resource_type="role",
                subresource_types=["role_policy"],
                secondary_attribute_names=["role_inline_policy_attachments", "role_managed_policy_attachments"],
            )
            in self.iam_service.resource_summary
        )

    def test_get_enabled_regions(self):
        assert self.service.enabled_regions == [
            "us-east-1",
            "ap-east-1",
            "eu-west-2",
        ]


class TestCloudWandererBoto3Resource(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        get_default_mocker().start_general_mock(restrict_regions=["eu-west-2", "us-east-1", "ap-east-1"])
        add_infra()

        cls.services = Boto3Services(boto3_session=DEFAULT_SESSION)

        cls.service = cls.services.get_service("ec2")
        cls.iam_service = cls.services.get_service("iam", region_name="us-east-1")
        cls.s3_service = cls.services.get_service("s3", region_name="us-east-1")

        cls.resource = next(cls.service.get_resources("vpc"))
        cls.role_resource = next(cls.iam_service.get_resources("role"))
        cls.bucket_resources = list(cls.s3_service.get_resources("bucket"))

    @classmethod
    def tearDownClass(cls) -> None:
        get_default_mocker().stop_general_mock()

    def test_raw_data(self):
        assert self.resource.raw_data == {
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
        }

    def test_normalised_raw_data(self):
        assert self.resource.normalised_raw_data == {
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
            "OwnerId": None,
            "State": "available",
            "Tags": [],
            "VpcId": ANY,
        }

    def test_resource_type(self):
        assert self.resource.resource_type == "vpc"

    def test_region_regional_resources(self):
        assert self.resource.region == "eu-west-2"

    def test_region_global_service_global_resources(self):
        resource_regions = [resource.region for resource in self.bucket_resources]

        assert sorted(resource_regions) == sorted(["us-east-1", "eu-west-2", "ap-east-1"])

    def test_account_id(self):
        assert self.resource.account_id == "123456789012"

    def test_service(self):
        assert self.resource.service == "ec2"

    def test_id(self):
        assert self.resource.id.startswith("vpc-")

    def test_secondary_attribute_names(self):
        assert self.resource.secondary_attribute_names == ["vpc_enable_dns_support"]

    def test_subresource_types(self):
        assert self.role_resource.subresource_types == ["role_policy"]

    def test_urn(self):
        assert isinstance(self.resource.urn, URN)
        assert str(self.resource.urn).startswith(
            "urn:aws:123456789012:eu-west-2:ec2:vpc"
        ), f"{str(self.resource.urn)} does not match 'urn:aws:123456789012:eu-west-2:ec2:vpc'"

    def test_get_secondary_attributes(self):
        result = next(self.resource.get_secondary_attributes())

        assert isinstance(result, SecondaryAttribute)
        assert result["EnableDnsSupport"] == {"Value": True}

    def test_get_subresources(self):
        result = next(self.role_resource.get_subresources())

        assert str(result.urn) == "urn:aws:123456789012:us-east-1:iam:role_policy:test-role/test-role-policy"
        assert result.raw_data == {
            "PolicyDocument": {
                "Statement": {"Action": "s3:ListBucket", "Effect": "Allow", "Resource": "arn:aws:s3:::example_bucket"},
                "Version": "2012-10-17",
            },
            "PolicyName": "test-role-policy",
            "ResponseMetadata": {
                "HTTPHeaders": {"server": "amazon.com"},
                "HTTPStatusCode": 200,
                "RequestId": ANY,
                "RetryAttempts": 0,
            },
            "RoleName": "test-role",
        }

    def test_get_and_cleanup_actions_regional_resource(self):
        assert self.resource.get_and_cleanup_actions == GetAndCleanUp(
            get_actions=[GetAction(service_name="ec2", region="eu-west-2", resource_type="vpc")],
            cleanup_actions=[CleanupAction(service_name="ec2", region="eu-west-2", resource_type="vpc")],
        )

    def test_get_and_cleanup_actions_global_service_regional_resource(self):
        assert self.bucket_resources[0].get_and_cleanup_actions == GetAndCleanUp(
            get_actions=[GetAction(service_name="s3", region="us-east-1", resource_type="bucket")],
            cleanup_actions=[
                CleanupAction(service_name="s3", region=region, resource_type="bucket")
                for region in self.service.enabled_regions
            ],
        )

    def test_get_and_cleanup_actions_global_service_global_resource(self):
        assert self.role_resource.get_and_cleanup_actions == GetAndCleanUp(
            get_actions=[GetAction(service_name="iam", region="us-east-1", resource_type="role")],
            cleanup_actions=[
                CleanupAction(service_name="iam", region="us-east-1", resource_type="role"),
                CleanupAction(service_name="iam", region="us-east-1", resource_type="role_policy"),
            ],
        )

    def test_secondary_attribute_models(self):
        assert [x.name for x in self.role_resource.secondary_attribute_models] == [
            "RoleInlinePolicyAttachments",
            "RoleManagedPolicyAttachments",
        ]
