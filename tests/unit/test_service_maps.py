import unittest
from unittest.mock import MagicMock

from cloudwanderer.boto3_loaders import ResourceMap, ResourceRegionRequest, ResourceRegionRequestParam, ServiceMap


class TestServiceMap(unittest.TestCase):
    def test_default_service_map(self):
        service_map = ServiceMap.factory(name="ec2", definition={})

        assert service_map.is_default_service
        assert not service_map.is_global_service

    def test_global_service_map(self):
        service_map = ServiceMap.factory(
            name="s3",
            definition={
                "service": {
                    "globalService": True,
                    "globalServiceRegion": "us-east-1",
                    "region": "us-east-1",
                },
                "resources": {
                    "Bucket": {
                        "type": "resource",
                        "regionRequest": {
                            "operation": "get_bucket_location",
                            "params": [{"target": "Bucket", "source": "resourceAttribute", "name": "name"}],
                            "pathToRegion": "LocationConstraint",
                            "defaultValue": "us-east-1",
                        },
                    }
                },
            },
        )

        assert not service_map.is_default_service
        assert service_map.is_global_service

        resource_map = service_map.get_resource_map("Bucket")
        assert isinstance(resource_map, ResourceMap)


class TestResourceMap(unittest.TestCase):
    def test_global_service_regional_resource_map(self):
        resource_map = ResourceMap.factory(
            service_name="s3",
            resource_type="bucket",
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
            boto3_definition={"resources": {}},
        )

        assert isinstance(resource_map.region_request, ResourceRegionRequest)
        assert resource_map.ignored_subresources == [{"type": "ObjectSummary"}]
        assert resource_map.ignored_subresource_types == ["ObjectSummary"]
        assert resource_map.requires_load_for_full_metadata
        assert not resource_map.regional_resource
        assert resource_map.default_filters == {"Key": "Value"}

    def test_subresource_map(self):
        resource_map = ResourceMap.factory(
            service_name="iam",
            resource_type="role_policy",
            definition={"type": "resource", "parentResourceType": "role"},
            boto3_definition={},
        )

        assert resource_map.parent_resource_type == "role"
        assert resource_map.default_filters == {}


class TestResourceRegionRequest(unittest.TestCase):
    def test_factory(self):
        request = ResourceRegionRequest.factory(
            {
                "operation": "get_bucket_location",
                "params": [{"target": "Bucket", "source": "resourceAttribute", "name": "name"}],
                "pathToRegion": "LocationConstraint",
                "defaultValue": "us-east-1",
            }
        )
        assert request.operation == "get_bucket_location"
        assert request.path_to_region == "LocationConstraint"
        assert isinstance(request.params[0], ResourceRegionRequestParam)

    def test_build_params(self):
        mock_bucket = MagicMock()
        mock_bucket.name = "test-s3-bucket"
        request = ResourceRegionRequest.factory(
            {
                "operation": "get_bucket_location",
                "params": [{"target": "Bucket", "source": "resourceAttribute", "name": "name"}],
                "pathToRegion": "LocationConstraint",
                "defaultValue": "us-east-1",
            }
        )

        assert request.build_params(mock_bucket) == {"Bucket": "test-s3-bucket"}
