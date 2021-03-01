import re
import unittest
from unittest.mock import ANY

import boto3

from cloudwanderer import CloudWanderer
from cloudwanderer.aws_interface import CloudWandererAWSInterface
from cloudwanderer.storage_connectors import MemoryStorageConnector

from ..helpers import DEFAULT_SESSION, GenericAssertionHelpers, get_default_mocker
from ..mocks import add_infra


class TestCloudWandererWriteResourcesConcurrently(unittest.TestCase, GenericAssertionHelpers):
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
            # This is a us-east-1 resource because s3 buckets are
            # discovered from us-east-1 irrespective of their region.
            "urn": "urn:aws:.*:eu-west-2:s3:bucket:.*",
            "attr": "BaseResource",
            "Name": "test-eu-west-2",
        },
    ]

    @classmethod
    def setUpClass(cls):
        cls.enabled_regions = ["eu-west-2", "us-east-1", "ap-east-1"]
        get_default_mocker().start_general_mock(
            restrict_regions=cls.enabled_regions,
            restrict_services=["ec2", "s3", "iam"],
            limit_resources=[
                "ec2:instance",
                "s3:bucket",
                "iam:group",
                "iam:role",
            ],
        )
        add_infra(regions=cls.enabled_regions)

    @classmethod
    def tearDownClass(cls):
        get_default_mocker().stop_general_mock()

    def setUp(self):
        self.wanderer = CloudWanderer(storage_connectors=[])

    def test_write_resources(self):

        thread_results = list(
            self.wanderer.write_resources_concurrently(
                cloud_interface_generator=lambda: CloudWandererAWSInterface(
                    boto3.Session(
                        aws_access_key_id="11111111", aws_secret_access_key="111111", aws_session_token="1111"
                    )
                ),
                storage_connector_generator=lambda: [MemoryStorageConnector()],
            )
        )
        connector_results = [
            resource_record
            for result in thread_results
            for connector in result.storage_connectors
            for resource_record in connector.read_all()
        ]

        for region_name in self.enabled_regions:
            self.assert_dictionary_overlap(
                connector_results,
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
                self.assert_dictionary_overlap(connector_results, self.us_east_1_resources)
            else:
                self.assert_no_dictionary_overlap(
                    connector_results,
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
        thread_results = list(
            self.wanderer.write_resources_concurrently(
                cloud_interface_generator=lambda: CloudWandererAWSInterface(DEFAULT_SESSION),
                storage_connector_generator=lambda: [MemoryStorageConnector()],
                exclude_resources=["ec2:instance"],
            )
        )
        connector_results = [
            resource_record
            for result in thread_results
            for connector in result.storage_connectors
            for resource_record in connector.read_all()
        ]
        for region_name in self.enabled_regions:
            self.assert_no_dictionary_overlap(
                connector_results,
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
        self.assert_dictionary_overlap(connector_results, self.us_east_1_resources)
