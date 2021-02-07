import unittest
from unittest.mock import ANY

from boto3.resources.model import Collection
from botocore.model import Shape

from cloudwanderer.aws_urn import AwsUrn
from cloudwanderer.boto3_helpers import (
    Boto3Helper,
    _clean_boto3_metadata,
    _get_resource_attributes,
    get_resource_collection_by_resource_type,
    get_resource_collections,
    get_resource_from_collection,
    get_service_resource_types_from_collections,
    get_shape,
)
from cloudwanderer.custom_resource_definitions import CustomResourceDefinitions
from cloudwanderer.service_mappings import ServiceMappingCollection

from ..helpers import DEFAULT_SESSION, get_default_mocker
from ..mocks import add_infra


class TestBoto3Helper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        get_default_mocker().start_general_mock(
            restrict_services=False, restrict_collections=False
        )
        add_infra()
        cls.custom_resource_definitions = CustomResourceDefinitions(DEFAULT_SESSION)
        cls.boto3_resources = {
            "iam:role": cls.custom_resource_definitions.resource("iam").Role(
                "test-role"
            ),
            "ec2:vpc": next(
                iter(cls.custom_resource_definitions.resource("ec2").vpcs.all())
            ),
        }

    @classmethod
    def tearDownClass(cls):
        get_default_mocker().stop_general_mock()

    def setUp(self):
        self.service_maps = ServiceMappingCollection(boto3_session=DEFAULT_SESSION)
        self.boto3_helper = Boto3Helper(DEFAULT_SESSION, service_maps=self.service_maps)
        self.boto3_service = DEFAULT_SESSION.resource("iam")

    def test_get_valid_resource_types(self):
        result = self.boto3_helper.get_valid_resource_types(
            service_name="iam", resource_types=["instance", "role"]
        )

        assert result == ["role"]

    def test_get_resource_collection_by_resource_type(self):
        result = get_resource_collection_by_resource_type(
            boto3_service=self.boto3_service, resource_type="role"
        )

        assert isinstance(result, Collection)

    def test_get_resource_from_collection(self):
        result = list(
            get_resource_from_collection(
                boto3_service=self.boto3_service,
                boto3_resource_collection=self.boto3_service.meta.resource_model.collections[
                    0
                ],
            )
        )

        assert result[0].name == "test-group"

    def test_get_service_resource_types_from_collections(self):
        result = list(
            get_service_resource_types_from_collections(
                collections=self.boto3_service.meta.resource_model.collections
            )
        )

        expected = {
            "group",
            "instance_profile",
            "policy",
            "role",
            "saml_provider",
            "server_certificate",
            "user",
            "virtual_mfa_device",
        }
        assert expected.issubset(result)

    def test_get_subresources(self):
        result = list(
            self.boto3_helper.get_subresources(
                boto3_resource=self.boto3_resources["iam:role"]
            )
        )

        assert result[0].name == "test-role-policy"

    def test_get_child_resources_subresources(self):
        result = list(
            self.boto3_helper.get_child_resources(
                boto3_resource=self.boto3_resources["iam:role"],
                resource_type="resource",
            )
        )

        assert result[0].name == "test-role-policy"

    def test_get_secondary_attributes(self):
        result = list(
            self.boto3_helper.get_secondary_attributes(
                boto3_resource=self.boto3_resources["ec2:vpc"]
            )
        )

        assert result[0].name == "vpc_enable_dns_support"

    def test_get_child_resources_secondary_attribute(self):
        result = list(
            self.boto3_helper.get_child_resources(
                boto3_resource=self.boto3_resources["ec2:vpc"],
                resource_type="secondaryAttribute",
            )
        )

        assert result[0].meta.data == {
            "EnableDnsSupport": {"Value": True},
            "ResponseMetadata": {
                "HTTPHeaders": {"server": "amazon.com"},
                "HTTPStatusCode": 200,
                "RequestId": ANY,
                "RetryAttempts": 0,
            },
            "VpcId": ANY,
        }

    def test_get_child_resource_definitions_subresources(self):
        result = list(
            self.boto3_helper.get_child_resource_definitions(
                service_name="iam",
                boto3_resource_model=self.boto3_resources[
                    "iam:role"
                ].meta.resource_model,
                resource_type="resource",
            )
        )

        assert result[0].name == "policies"

    def test_get_child_resource_definitions_secondary_attributes(self):
        result = list(
            self.boto3_helper.get_child_resource_definitions(
                service_name="ec2",
                boto3_resource_model=self.boto3_resources[
                    "ec2:vpc"
                ].meta.resource_model,
                resource_type="secondaryAttribute",
            )
        )

        assert result[0].name == "VpcEnableDnsSupport"

    def test_get_resource_urn(self):
        result = self.boto3_helper.get_resource_urn(
            resource=self.boto3_resources["iam:role"], region_name="us-east-1"
        )

        assert result == AwsUrn(
            account_id="123456789012",
            region="us-east-1",
            service="iam",
            resource_type="role",
            resource_id="test-role",
        )

    def test__get_resource_attributes(self):
        result = _get_resource_attributes(
            boto3_resource=self.boto3_resources["iam:role"]
        )

        expected_keys = {
            "Path",
            "RoleName",
            "RoleId",
            "Arn",
            "CreateDate",
            "AssumeRolePolicyDocument",
            "Description",
            "MaxSessionDuration",
            "PermissionsBoundary",
            "Tags",
            "RoleLastUsed",
        }
        assert expected_keys.issubset(set(result.keys()))
        assert all(isinstance(shape, Shape) for shape in result.values())

    def test_get_shape(self):
        result = get_shape(self.boto3_resources["iam:role"])

        assert isinstance(result, Shape)

    def test__clean_boto3_metadata(self):
        result = _clean_boto3_metadata(
            boto3_metadata={
                "ShouldIBeHere": "Yes",
                "ResponseMetadata": {"ShouldIBeHere": "No"},
            }
        )

        assert result == {"ShouldIBeHere": "Yes"}

    def test_get_resource_collections(self):
        result = get_resource_collections(boto3_service=self.boto3_service)

        assert all(isinstance(resource, Collection) for resource in result)
        assert len(result) >= 7
