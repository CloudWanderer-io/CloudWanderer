from unittest.mock import MagicMock

from cloudwanderer.aws_interface.models import (
    ResourceMap,
    ResourceRegionRequest,
    ResourceRegionRequestParam,
    ServiceMap,
)


def test_default_service_map():
    service_map = ServiceMap.factory(name="ec2", definition={})

    assert service_map.is_default_service
    assert not service_map.is_global_service


def test_global_service_map():
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


def test_factory():
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


def test_build_params():
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
