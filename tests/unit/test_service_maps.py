import unittest
from unittest.mock import MagicMock

from cloudwanderer.boto3_loaders import ResourceMap, ResourceRegionRequest, ResourceRegionRequestParam, ServiceMap


class TestServiceMap(unittest.TestCase):
    def test_default_service_map(self):
        service_map = ServiceMap.factory(name="ec2", definition={})

        assert service_map.is_default_service
        assert not service_map.is_global_service
        assert service_map.regional_resources

    def test_global_service_map(self):
        service_map = ServiceMap.factory(
            name="s3",
            definition={
                "service": {
                    "globalService": True,
                    "globalServiceRegion": "us-east-1",
                    "region": "us-east-1",
                    "regionalResources": True,
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
        assert service_map.regional_resources

        resource_map = service_map.get_resource_map("Bucket")
        assert isinstance(resource_map, ResourceMap)


class TestResourceMap(unittest.TestCase):
    def test_global_service_regional_resource_map(self):
        resource_map = ResourceMap.factory(
            definition={
                "type": "resource",
                "regionRequest": {
                    "operation": "get_bucket_location",
                    "params": [{"target": "Bucket", "source": "resourceAttribute", "name": "name"}],
                    "pathToRegion": "LocationConstraint",
                    "defaultValue": "us-east-1",
                },
            }
        )

        assert isinstance(resource_map.region_request, ResourceRegionRequest)


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
