import unittest
from unittest.mock import MagicMock

import boto3
from boto3.resources.model import ResourceModel

from cloudwanderer.boto3_loaders import ResourceMap, ResourceRegionRequest
from cloudwanderer.models import AWSGetAndCleanUp, CleanupAction, GetAction

from .helpers import named_mock


class TestResourceMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ec2_service_model = boto3.session.Session()._loader.load_service_model("ec2", "resources-1", "2016-11-15")
        s3_service_model = boto3.session.Session()._loader.load_service_model("s3", "resources-1", "2006-03-01")
        iam_service_model = boto3.session.Session()._loader.load_service_model("iam", "resources-1", "2010-05-08")
        cls.vpc_resource_model = ResourceModel(
            name="Vpc",
            definition=ec2_service_model["resources"]["Vpc"],
            resource_defs=ec2_service_model["resources"],
        )
        cls.bucket_resource_model = ResourceModel(
            name="Bucket",
            definition=s3_service_model["resources"]["Bucket"],
            resource_defs=s3_service_model["resources"],
        )
        cls.role_resource_model = ResourceModel(
            name="Role",
            definition=iam_service_model["resources"]["Role"],
            resource_defs=iam_service_model["resources"],
        )

    def test_global_service_regional_resource_map(self):
        resource_map = ResourceMap.factory(
            definition={
                "type": "resource",
                "regionalResource": False,
                "regionRequest": {
                    "operation": "get_bucket_location",
                    "params": [{"target": "Bucket", "source": "resourceAttribute", "name": "name"}],
                    "pathToRegion": "LocationConstraint",
                    "defaultValue": "us-east-1",
                },
                "ignoredSubresources": [{"type": "ObjectSummary"}],
                "requiresLoadForFullMetadata": True,
                "defaultFilters": {"Key": "Value"},
            },
            boto3_resource_model=self.bucket_resource_model,
            service_map=MagicMock(),
        )

        assert isinstance(resource_map.region_request, ResourceRegionRequest)
        assert resource_map.ignored_subresources == [{"type": "ObjectSummary"}]
        assert resource_map.ignored_subresource_types == ["ObjectSummary"]
        assert resource_map.requires_load_for_full_metadata
        assert not resource_map.regional_resource
        assert resource_map.default_filters == {"Key": "Value"}

    def test_subresource_map(self):
        resource_map = ResourceMap.factory(
            definition={"type": "resource", "parentResourceType": "role"},
            boto3_resource_model=self.bucket_resource_model,
            service_map=MagicMock(),
        )

        assert resource_map.parent_resource_type == "role"
        assert resource_map.default_filters == {}

    def test_should_query_resources_in_region_global_service(self):
        resource_map = ResourceMap.factory(
            definition={},
            boto3_resource_model=self.bucket_resource_model,
            service_map=MagicMock(is_global_service=True, global_service_region="us-east-1"),
        )

        assert resource_map.should_query_resources_in_region("us-east-1")
        assert not resource_map.should_query_resources_in_region("eu-west-1")

    def test_should_query_resources_in_region_regional_service(self):
        resource_map = ResourceMap.factory(
            definition={},
            boto3_resource_model=self.bucket_resource_model,
            service_map=MagicMock(is_global_service=False),
        )

        assert resource_map.should_query_resources_in_region("us-east-1")
        assert resource_map.should_query_resources_in_region("eu-west-1")

    def test_subresource_models(self):
        resource_map = ResourceMap.factory(
            definition={"type": "resource"},
            boto3_resource_model=self.role_resource_model,
            service_map=MagicMock(),
        )

        assert [subresource.name for subresource in resource_map.subresource_models] == ["policies"]

    def test_subresource_types(self):
        resource_map = ResourceMap.factory(
            definition={"type": "resource"},
            boto3_resource_model=self.role_resource_model,
            service_map=MagicMock(),
        )

        assert resource_map.subresource_types == ["role_policy"]

    def test_get_and_cleanup_actions_global_service_global_resource(self):
        resource_map = ResourceMap.factory(
            definition={"type": "resource", "regionalResource": False},
            boto3_resource_model=self.role_resource_model,
            service_map=named_mock("iam", is_global_service=True, global_service_region="us-east-1"),
        )

        assert resource_map.get_and_cleanup_actions(query_region="us-east-1") == AWSGetAndCleanUp(
            get_actions=[
                GetAction(service_name="iam", region="us-east-1", resource_type="role"),
            ],
            cleanup_actions=[
                CleanupAction(service_name="iam", region="us-east-1", resource_type="role"),
            ],
        )

    def test_get_and_cleanup_actions_global_service_regional_resource(self):
        resource_map = ResourceMap.factory(
            definition={"type": "resource", "regionalResource": True},
            boto3_resource_model=self.bucket_resource_model,
            service_map=named_mock("s3", is_global_service=True, global_service_region="us-east-1"),
        )

        assert resource_map.get_and_cleanup_actions(query_region="us-east-1") == AWSGetAndCleanUp(
            get_actions=[
                GetAction(service_name="s3", region="us-east-1", resource_type="bucket"),
            ],
            cleanup_actions=[
                CleanupAction(service_name="s3", region="ALL_REGIONS", resource_type="bucket"),
            ],
        )

    def test_get_and_cleanup_actions_regional_service_regional_resource(self):
        resource_map = ResourceMap.factory(
            definition={"type": "resource", "regionalResource": True},
            boto3_resource_model=self.vpc_resource_model,
            service_map=named_mock("ec2", is_global_service=False),
        )

        assert resource_map.get_and_cleanup_actions(query_region="us-east-1") == AWSGetAndCleanUp(
            get_actions=[
                GetAction(service_name="ec2", region="us-east-1", resource_type="vpc"),
            ],
            cleanup_actions=[
                CleanupAction(service_name="ec2", region="us-east-1", resource_type="vpc"),
            ],
        )

    def test_get_and_cleanup_actions_global_service_regional_subresource(self):
        resource_map = ResourceMap.factory(
            definition={"type": "subresource", "regionalResource": True},
            boto3_resource_model=self.bucket_resource_model,
            service_map=named_mock("s3", is_global_service=True, global_service_region="us-east-1"),
        )

        assert resource_map.get_and_cleanup_actions(query_region="us-east-1") == AWSGetAndCleanUp(
            get_actions=[],
            cleanup_actions=[
                CleanupAction(service_name="s3", region="ALL_REGIONS", resource_type="bucket"),
            ],
        )

    def test_get_and_cleanup_actions_regional_service_regional_subresource(self):
        resource_map = ResourceMap.factory(
            definition={"type": "subresource", "regionalResource": True},
            boto3_resource_model=self.vpc_resource_model,
            service_map=named_mock("ec2", is_global_service=False),
        )

        assert resource_map.get_and_cleanup_actions(query_region="us-east-1") == AWSGetAndCleanUp(
            get_actions=[],
            cleanup_actions=[
                CleanupAction(service_name="ec2", region="us-east-1", resource_type="vpc"),
            ],
        )
