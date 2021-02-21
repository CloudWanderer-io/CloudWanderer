import unittest

from cloudwanderer import URN
from cloudwanderer.boto3_getter import Boto3Getter
from cloudwanderer.exceptions import (
    BadRequestError,
    BadUrnAccountIdError,
    BadUrnRegionError,
    BadUrnSubResourceError,
    ResourceActionDoesNotExistError,
    ResourceNotFoundError,
    UnsupportedResourceTypeError,
)
from cloudwanderer.service_mappings import ServiceMappingCollection

from ..helpers import DEFAULT_SESSION, GenericAssertionHelpers, get_default_mocker


class TestBoto3GetterGetResource(unittest.TestCase, GenericAssertionHelpers):
    @classmethod
    def setUpClass(cls):
        cls.enabled_regions = ["eu-west-2", "us-east-1", "ap-east-1"]
        mocker = get_default_mocker()
        mocker.start_moto_services(mocker.default_moto_services + ["mock_secretsmanager"])

    @classmethod
    def tearDownClass(cls):
        get_default_mocker().stop_general_mock()

    def setUp(self):
        self.boto3_getter = Boto3Getter(DEFAULT_SESSION, ServiceMappingCollection(DEFAULT_SESSION))

    def test_get_custom_subresource(self):
        with self.assertRaises(BadUrnSubResourceError):
            self.boto3_getter.get_resource_from_urn(
                urn=URN(
                    account_id="123456789012",
                    region="us-east-1",
                    service="iam",
                    resource_type="role_policy",
                    resource_id="test-role/test-policy",
                )
            )

    def test_get_s3_bucket_bad_account_id(self):
        with self.assertRaises(BadUrnAccountIdError):
            self.boto3_getter.get_resource_from_urn(
                urn=URN(
                    account_id="111111111111",
                    region="eu-west-2",
                    service="s3",
                    resource_type="bucket",
                    resource_id="test-eu-west-2",
                )
            )

    def test_get_invalid_iam_role_eu_west_2(self):
        with self.assertRaises(BadUrnRegionError):
            self.boto3_getter.get_resource_from_urn(
                urn=URN(
                    account_id="123456789012",
                    region="eu-west-2",
                    service="iam",
                    resource_type="role",
                    resource_id="test-role",
                )
            )

    def test_get_missing_iam_role(self):
        with self.assertRaisesRegex(
            ResourceNotFoundError, "urn:aws:123456789012:us-east-1:iam:role:non-existent-role was not found"
        ):
            self.boto3_getter.get_resource_from_urn(
                urn=URN(
                    account_id="123456789012",
                    region="us-east-1",
                    service="iam",
                    resource_type="role",
                    resource_id="non-existent-role",
                )
            )

    def test_get_missing_ec2_instance_eu_west_2(self):
        with self.assertRaisesRegex(
            BadRequestError,
            "A request error was returned while fetching urn:aws:123456789012:eu-west-2:ec2:instance:i-111111111111",
        ):
            self.boto3_getter.get_resource_from_urn(
                urn=URN(
                    account_id="123456789012",
                    region="eu-west-2",
                    service="ec2",
                    resource_type="instance",
                    resource_id="i-111111111111",
                )
            )

    def test_get_invalid_type_resource(self):
        with self.assertRaisesRegex(
            ResourceActionDoesNotExistError, "secr3t does not exist as a supported resource for secretsmanager"
        ):
            self.boto3_getter.get_resource_from_urn(
                urn=URN(
                    account_id="123456789012",
                    region="eu-west-2",
                    service="secretsmanager",
                    resource_type="secr3t",
                    resource_id="test-secret",
                )
            )

    def test_unsupported_resource_type(self):
        with self.assertRaisesRegex(UnsupportedResourceTypeError, "event does not support loading by ID"):
            self.boto3_getter.get_resource_from_urn(
                urn=URN(
                    account_id="123456789012",
                    region="eu-west-2",
                    service="cloudformation",
                    resource_type="event",
                    resource_id="fake-event",
                )
            )

    def test_get_boto3_subresource(self):
        with self.assertRaisesRegex(
            BadUrnSubResourceError,
            "urn:aws:123456789012:eu-west-2:ec2:route:fake-route is a sub resource, "
            "please call get_resource against its parent.",
        ):
            result = self.boto3_getter.get_resource_from_urn(
                urn=URN(
                    account_id="123456789012",
                    region="eu-west-2",
                    service="ec2",
                    resource_type="route",
                    resource_id="fake-route",
                )
            )
            print(result)
