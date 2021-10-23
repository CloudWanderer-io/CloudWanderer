from unittest.mock import MagicMock

from moto import mock_ec2, mock_iam, mock_s3, mock_sts

from cloudwanderer.storage_connectors import MemoryStorageConnector
from cloudwanderer.urn import URN
from tests.integration.pytest_helpers import create_iam_role, create_s3_buckets


@mock_sts
@mock_ec2
@mock_s3
@mock_iam
def test_write_resources(cloudwanderer_aws, aws_interface, default_test_discovery_actions):
    create_iam_role()
    create_s3_buckets(regions=["eu-west-2", "us-east-1"])
    aws_interface.get_resource_discovery_actions = MagicMock(return_value=default_test_discovery_actions)

    thread_results = list(
        cloudwanderer_aws.write_resources_concurrently(
            concurrency=2,
            cloud_interface_generator=lambda: aws_interface,
            storage_connector_generator=lambda: [MemoryStorageConnector()],
        )
    )

    connector_results = [
        resource_record
        for result in thread_results
        for connector in result.storage_connectors
        for resource_record in connector.read_all()
    ]

    result_summary = set(
        [
            (URN.from_string(result["urn"]).region, URN.from_string(result["urn"]).resource_type)
            for result in connector_results
        ]
    )

    assert result_summary == {
        ("eu-west-2", "bucket"),
        ("eu-west-2", "vpc"),
        ("us-east-1", "bucket"),
        ("us-east-1", "role"),
        ("us-east-1", "role_policy"),
        ("us-east-1", "vpc"),
    }


# TODO: Reinstate exclude_resources
# def test_write_resources_exclude_resources(self):
#     thread_results = list(
#         cloudwanderer_aws.write_resources_concurrently(
#             cloud_interface_generator=lambda: CloudWandererAWSInterface(DEFAULT_SESSION),
#             storage_connector_generator=lambda: [MemoryStorageConnector()],
#             exclude_resources=["ec2:instance"],
#         )
#     )
#     connector_results = [
#         resource_record
#         for result in thread_results
#         for connector in result.storage_connectors
#         for resource_record in connector.read_all()
#     ]
#     for region_name in self.enabled_regions:
#         self.assert_no_dictionary_overlap(
#             connector_results,
#             [
#                 {
#                     "urn": f"urn:aws:.*:{region_name}:ec2:instance:.*",
#                     "attr": "BaseResource",
#                     "VpcId": "vpc-.*",
#                     "SubnetId": "subnet-.*",
#                     "InstanceId": "i-.*",
#                 }
#             ],
#         )
#     self.assert_dictionary_overlap(connector_results, US_EAST_1_RESOURCES)
