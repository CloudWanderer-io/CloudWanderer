import re
import unittest
from unittest.mock import ANY

import boto3

from cloudwanderer import CloudWanderer
from cloudwanderer.storage_connectors import MemoryStorageConnector

from ..helpers import GenericAssertionHelpers, get_default_mocker
from ..mocks import add_infra


class TestCloudWandererWriteResources(unittest.TestCase, GenericAssertionHelpers):
    eu_west_2_resources = [
        {
            "urn": "urn:aws:.*:eu-west-2:ec2:instance:.*",
            "attr": "BaseResource",
            "VpcId": "vpc-.*",
            "SubnetId": "subnet-.*",
            "InstanceId": "i-.*",
        }
    ]
    us_east_1_resources = [
        {
            "urn": "urn:aws:.*:us-east-1:iam:role:.*",
            "attr": "BaseResource",
            "RoleName": "test-role",
            "Path": re.escape("/"),
        },
        {
            "urn": "urn:aws:.*:us-east-1:iam:role:.*",
            "attr": "role_inline_policy_attachments",
            "PolicyNames": ["test-role-policy"],
        },
        {
            "urn": "urn:aws:.*:us-east-1:iam:role:.*",
            "attr": "role_managed_policy_attachments",
            "AttachedPolicies": [
                {
                    "PolicyName": "APIGatewayServiceRolePolicy",
                    "PolicyArn": "arn:aws:iam::aws:policy/aws-service-role/APIGatewayServiceRolePolicy",
                }
            ],
            "IsTruncated": False,
        },
        {
            "urn": "urn:aws:.*:us-east-1:iam:role_policy:.*",
            "attr": "BaseResource",
            "PolicyName": "test-role-policy",
            "PolicyDocument": ANY,
        },
        {
            # This is a us-east-1 resource because s3 buckets are discovered from us-east-1
            # irrespective of their region.
            "urn": "urn:aws:.*:eu-west-2:s3:bucket:.*",
            "attr": "BaseResource",
            "Name": "test-eu-west-2",
        },
    ]

    def setUp(self):
        self.enabled_regions = ["eu-west-2", "us-east-1", "ap-east-1"]
        get_default_mocker().start_general_mock(
            restrict_regions=self.enabled_regions,
            restrict_services=["ec2", "s3", "iam"],
            limit_resources=[
                "ec2:instance",
                "s3:bucket",
                "iam:group",
                "iam:role",
            ],
        )
        add_infra(regions=self.enabled_regions)
        self.storage_connector = MemoryStorageConnector()
        self.wanderer = CloudWanderer(storage_connectors=[self.storage_connector])

    def tearDown(self):
        get_default_mocker().stop_general_mock()

    def test_write_resources(self):

        self.wanderer.write_resources()

        for region_name in self.enabled_regions:
            self.assert_dictionary_overlap(
                self.storage_connector.read_all(),
                [
                    {
                        "urn": f"urn:aws:.*:{region_name}:ec2:instance:.*",
                        "attr": "BaseResource",
                        "VpcId": "vpc-.*",
                        "SubnetId": "subnet-.*",
                        "InstanceId": "i-.*",
                    },
                    {
                        "urn": f"urn:aws:.*:{region_name}:s3:bucket:.*",
                        "attr": "BaseResource",
                        "Name": f"test-{region_name}",
                    },
                ],
            )

            if region_name == "us-east-1":
                self.assert_dictionary_overlap(self.storage_connector.read_all(), self.us_east_1_resources)
            else:
                self.assert_no_dictionary_overlap(
                    self.storage_connector.read_all(),
                    [
                        {
                            "urn": f"urn:aws:.*:{region_name}:iam:role:.*",
                            "attr": "BaseResource",
                            "RoleName": "test-role",
                            "Path": re.escape("/"),
                        }
                    ],
                )

    def test_write_resources_exclude_resources(self):
        self.wanderer.write_resources(exclude_resources=["ec2:instance"])

        for region_name in self.enabled_regions:
            self.assert_no_dictionary_overlap(
                self.storage_connector.read_all(),
                [
                    {
                        "urn": f"urn:aws:.*:{region_name}:ec2:instance:.*",
                        "attr": "BaseResource",
                        "VpcId": "vpc-.*",
                        "SubnetId": "subnet-.*",
                        "InstanceId": "i-.*",
                    }
                ],
            )
        self.assert_dictionary_overlap(self.storage_connector.read_all(), self.us_east_1_resources)

    def test_write_resources_eu_west_1(self):
        self.wanderer.write_resources(
            regions=["eu-west-2"],
        )

        self.assert_dictionary_overlap(self.storage_connector.read_all(), self.eu_west_2_resources)
        self.assert_no_dictionary_overlap(self.storage_connector.read_all(), self.us_east_1_resources)

    def test_write_resources_us_east_1(self):
        self.wanderer.write_resources(regions=["us-east-1"])

        self.assert_dictionary_overlap(self.storage_connector.read_all(), self.us_east_1_resources)
        self.assert_no_dictionary_overlap(self.storage_connector.read_all(), self.eu_west_2_resources)

    def test_write_resources_of_service_eu_west_1(self):
        self.wanderer.write_resources(regions=["eu-west-2"], service_names=["ec2"])
        self.wanderer.write_resources(regions=["eu-west-2"], service_names=["s3"])

        self.assert_dictionary_overlap(self.storage_connector.read_all(), self.eu_west_2_resources)
        self.assert_no_dictionary_overlap(self.storage_connector.read_all(), self.us_east_1_resources)

    def test_write_resources_of_service_us_east_1(self):
        self.wanderer.write_resources(service_names=["ec2"], regions=["us-east-1"])
        self.wanderer.write_resources(service_names=["s3"], regions=["us-east-1"])
        self.wanderer.write_resources(service_names=["iam"], regions=["us-east-1"])

        self.assert_dictionary_overlap(self.storage_connector.read_all(), self.us_east_1_resources)
        self.assert_no_dictionary_overlap(self.storage_connector.read_all(), self.eu_west_2_resources)

    def test_write_resources_of_type_eu_west_1(self):
        self.wanderer.write_resources(regions=["eu-west-2"], service_names=["s3"], resource_types=["bucket"])
        self.wanderer.write_resources(regions=["eu-west-2"], service_names=["ec2"], resource_types=["instance"])
        self.wanderer.write_resources(regions=["eu-west-2"], service_names=["iam"], resource_types=["role"])

        self.assert_dictionary_overlap(self.storage_connector.read_all(), self.eu_west_2_resources)
        self.assert_no_dictionary_overlap(self.storage_connector.read_all(), self.us_east_1_resources)

    def test_write_resources_of_type_us_east_1(self):
        self.wanderer.write_resources(service_names=["s3"], resource_types=["bucket"], regions=["us-east-1"])
        self.wanderer.write_resources(service_names=["ec2"], resource_types=["instance"], regions=["us-east-1"])
        self.wanderer.write_resources(service_names=["iam"], resource_types=["role"], regions=["us-east-1"])

        self.assert_dictionary_overlap(self.storage_connector.read_all(), self.us_east_1_resources)
        self.assert_no_dictionary_overlap(self.storage_connector.read_all(), self.eu_west_2_resources)

    def test_cleanup_resources_of_type_us_east_1(self):
        self.wanderer.write_resources(service_names=["iam"], resource_types=["role"], regions=["us-east-1"])

        self.assert_dictionary_overlap(
            self.storage_connector.read_all(),
            [
                {
                    "urn": "urn:aws:.*:us-east-1:iam:role:.*",
                    "attr": "role_managed_policy_attachments",
                    "AttachedPolicies": [
                        {
                            "PolicyName": "APIGatewayServiceRolePolicy",
                            "PolicyArn": "arn:aws:iam::aws:policy/aws-service-role/APIGatewayServiceRolePolicy",
                        }
                    ],
                    "IsTruncated": False,
                },
                {
                    "urn": "urn:aws:.*:us-east-1:iam:role_policy:.*",
                    "attr": "BaseResource",
                    "PolicyName": "test-role-policy",
                    "PolicyDocument": ANY,
                },
            ],
        )

        # Delete the role
        iam_resource = boto3.resource("iam")
        iam_resource.Role("test-role").detach_policy(
            PolicyArn="arn:aws:iam::aws:policy/aws-service-role/APIGatewayServiceRolePolicy"
        )
        iam_resource.Role("test-role").Policy("test-role-policy").delete()
        iam_resource.Role("test-role").delete()

        self.wanderer.write_resources(service_names=["iam"], resource_types=["role"], regions=["us-east-1"])
        self.assert_no_dictionary_overlap(
            self.storage_connector.read_all(),
            [
                {
                    "urn": "urn:aws:.*:us-east-1:iam:role:.*",
                    "attr": "role_managed_policy_attachments",
                    "AttachedPolicies": [
                        {
                            "PolicyName": "APIGatewayServiceRolePolicy",
                            "PolicyArn": "arn:aws:iam::aws:policy/aws-service-role/APIGatewayServiceRolePolicy",
                        }
                    ],
                    "IsTruncated": False,
                },
                {
                    "urn": "urn:aws:.*:us-east-1:iam:role_policy:.*",
                    "attr": "BaseResource",
                    "PolicyName": "test-role-policy",
                    "PolicyDocument": ANY,
                },
            ],
        )
