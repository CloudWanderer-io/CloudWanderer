import re
import unittest
from unittest.mock import ANY

from cloudwanderer import CloudWandererAWSInterface

from ..helpers import GenericAssertionHelpers, get_default_mocker
from ..mocks import add_infra


class TestCloudWandererGetResources(unittest.TestCase, GenericAssertionHelpers):
    eu_west_2_resources = [
        {
            "urn": "urn:aws:.*:eu-west-2:ec2:instance:.*",
            "vpc_id": "vpc-.*",
            "subnet_id": "subnet-.*",
            "instance_id": "i-.*",
        }
    ]
    us_east_1_resources = [
        {
            "urn": "urn:aws:.*:us-east-1:iam:role:.*",
            "role_name": "test-role",
            "path": re.escape("/"),
            "[].PolicyNames[0]": ["test-role-policy"],
            "[].AttachedPolicies[0]": [
                {
                    "PolicyName": "APIGatewayServiceRolePolicy",
                    "PolicyArn": "arn:aws:iam::aws:policy/aws-service-role/APIGatewayServiceRolePolicy",
                }
            ],
            "[].IsTruncated": [False, False],
        },
        {"urn": "urn:aws:.*:us-east-1:iam:role_policy:.*", "policy_name": "test-role-policy", "policy_document": ANY},
        {
            # This is a us-east-1 resource because s3 buckets are discovered
            # from us-east-1 irrespective of their region.
            "urn": "urn:aws:.*:eu-west-2:s3:bucket:.*",
            "name": "test-eu-west-2",
        },
    ]

    @classmethod
    def setUpClass(cls):
        cls.enabled_regions = ["eu-west-2", "us-east-1", "ap-east-1"]
        get_default_mocker().start_general_mock(
            restrict_regions=cls.enabled_regions,
            restrict_services=["ec2", "s3", "iam"],
            limit_resources=["ec2:instance", "s3:bucket", "iam:group", "iam:role"],
        )
        add_infra(regions=cls.enabled_regions)

    @classmethod
    def tearDownClass(cls):
        get_default_mocker().stop_general_mock()

    def setUp(self):
        self.aws_interface = CloudWandererAWSInterface()

    def test_get_resources(self):

        result = list(self.aws_interface.get_resources())

        for region_name in self.enabled_regions:
            self.assert_dictionary_overlap(
                result,
                [
                    {
                        "urn": f"urn:aws:.*:{region_name}:ec2:instance:.*",
                        "vpc_id": "vpc-.*",
                        "subnet_id": "subnet-.*",
                        "instance_id": "i-.*",
                    },
                    {
                        "urn": f"urn:aws:.*:{region_name}:s3:bucket:.*",
                        "name": f"test-{region_name}",
                    },
                ],
            )

            if region_name == "us-east-1":
                self.assert_dictionary_overlap(result, self.us_east_1_resources)
            else:
                self.assert_no_dictionary_overlap(
                    result,
                    [
                        {
                            "urn": f"urn:aws:.*:{region_name}:iam:role:.*",
                            "role_name": "test-role",
                            "path": re.escape("/"),
                        }
                    ],
                )

    def test_get_resources_exclude_resources(self):
        result = list(self.aws_interface.get_resources(exclude_resources=["ec2:instance"]))

        for region_name in self.enabled_regions:
            self.assert_no_dictionary_overlap(
                result,
                [
                    {
                        "urn": f"urn:aws:.*:{region_name}:ec2:instance:.*",
                        "vpc_id": "vpc-.*",
                        "subnet_id": "subnet-.*",
                        "instance_id": "i-.*",
                    }
                ],
            )
        self.assert_dictionary_overlap(result, self.us_east_1_resources)

    def test_get_resources_in_region_eu_west_2(self):
        result = self.aws_interface.get_resources(regions=["eu-west-2"])

        self.assert_dictionary_overlap(result, self.eu_west_2_resources)
        self.assert_no_dictionary_overlap(result, self.us_east_1_resources)

    def test_get_resources_in_region_us_east_1(self):
        result = list(self.aws_interface.get_resources(regions=["us-east-1"]))

        self.assert_dictionary_overlap(result, self.us_east_1_resources)
        self.assert_no_dictionary_overlap(result, self.eu_west_2_resources)

    def test_get_resources_of_service_eu_west_2(self):
        result = list(self.aws_interface.get_resources(regions=["eu-west-2"], service_names=["ec2", "s3"]))

        self.assert_dictionary_overlap(result, self.eu_west_2_resources)
        self.assert_no_dictionary_overlap(result, self.us_east_1_resources)

    def test_get_resources_of_service_us_east_1(self):
        result = list(self.aws_interface.get_resources(service_names=["ec2", "s3", "iam"], regions=["us-east-1"]))

        self.assert_dictionary_overlap(result, self.us_east_1_resources)
        self.assert_no_dictionary_overlap(result, self.eu_west_2_resources)

    def test_get_resources_of_type_in_region_eu_west_2(self):
        result = list(
            self.aws_interface.get_resources(
                service_names=["ec2", "s3", "iam"], resource_types=["instance", "bucket", "role"], regions=["eu-west-2"]
            )
        )

        self.assert_dictionary_overlap(result, self.eu_west_2_resources)
        self.assert_no_dictionary_overlap(result, self.us_east_1_resources)

    def test_get_resources_of_type_in_region_us_east_1(self):
        result = self.aws_interface.get_resources(
            service_names=["ec2", "s3", "iam"], resource_types=["instance", "bucket", "role"], regions=["us-east-1"]
        )
        self.assert_dictionary_overlap(result, self.us_east_1_resources)
        self.assert_no_dictionary_overlap(result, self.eu_west_2_resources)
