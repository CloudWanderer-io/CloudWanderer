import unittest

from cloudwanderer.boto3_services import Boto3Services, CloudWandererBoto3Resource, ResourceSummary

from ..helpers import DEFAULT_SESSION, get_default_mocker
from ..mocks import add_infra


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
        assert {"instance", "internet_gateway", "vpc"}.issubset(set(self.service.resource_types))

    def test_get_resources(self):
        assert isinstance(next(self.service.get_resources("vpc")), CloudWandererBoto3Resource)

    def test_get_resources_filtered(self):
        results = self.service.get_resources("vpc", resource_filters={"MaxResults": 5})
        assert isinstance(next(results), CloudWandererBoto3Resource)

    def test_get_resources_from_urn(self):
        vpc = next(self.service.get_resources("vpc"))
        print(vpc.urn)
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

    def test_account_id(self):
        assert self.service.account_id == "123456789012"

    def test_resource_summary(self):
        assert (
            ResourceSummary(
                resource_type="vpc",
                resource_type_pascal="Vpc",
                service_friendly_name="EC2",
                subresources=[],
                secondary_attribute_names=["vpc_enable_dns_support"],
            )
            in self.service.resource_summary
        )

        assert (
            ResourceSummary(
                resource_type="role",
                resource_type_pascal="Role",
                service_friendly_name="IAM",
                subresources=[
                    ResourceSummary(
                        resource_type="role_policy",
                        resource_type_pascal="RolePolicy",
                        service_friendly_name="IAM",
                        subresources=[],
                        secondary_attribute_names=["role_inline_policy_attachments", "role_managed_policy_attachments"],
                    )
                ],
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
