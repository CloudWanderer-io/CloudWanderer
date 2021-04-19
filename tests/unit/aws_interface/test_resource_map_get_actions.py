import unittest
from unittest.mock import MagicMock

from cloudwanderer.boto3_loaders import ResourceMap
from cloudwanderer.models import AWSGetAndCleanUp, CleanupAction, GetAction

from ..helpers import named_mock


class TestCloudWandererBoto3ResourceGetActions(unittest.TestCase):
    def test_global_service_regional_resource(self):
        resource = ResourceMap(
            service_map=named_mock("test", is_global_service=True, global_service_region="us-east-1"),
            type="resource",
            region_request=MagicMock(),
            resource_type="test_resource",
            parent_resource_type=None,
            ignored_subresources=[],
            boto3_resource_model={},
            default_filters={},
        )

        assert resource.get_and_cleanup_actions(query_region="us-east-1") == AWSGetAndCleanUp(
            get_actions=[GetAction(service_name="test", region="us-east-1", resource_type="test_resource")],
            cleanup_actions=[
                CleanupAction(service_name="test", region="ALL_REGIONS", resource_type="test_resource"),
            ],
        )

    def test_global_service_regional_resource_wrong_region(self):
        resource = ResourceMap(
            service_map=named_mock("test", is_global_service=True, global_service_region="us-east-1"),
            type="resource",
            region_request=MagicMock(),
            resource_type="test_resource",
            parent_resource_type=None,
            ignored_subresources=[],
            boto3_resource_model={},
            default_filters={},
        )

        assert resource.get_and_cleanup_actions(query_region="eu-west-1") == AWSGetAndCleanUp(
            get_actions=[],
            cleanup_actions=[],
        )

    # def test_should_query_resources_in_region_regional_service(self):
    #     assert self.resource.should_query_resources_in_region

    # def test_should_query_resources_in_region_global_service_regional_resources(self):
    #     assert self.bucket_resources[0].should_query_resources_in_region

    # def test_should_query_resources_in_region_global_service_regional_resources_wrong_query_region(self):
    #     s3_service = self.services.get_service("s3", region_name="eu-west-2")
    #     assert not s3_service.should_query_resources_in_region

    # def test_should_query_resources_in_region_global_service_global_resources(self):
    #     assert self.iam_service.should_query_resources_in_region
