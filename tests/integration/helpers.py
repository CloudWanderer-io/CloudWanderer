from unittest.mock import patch, MagicMock
import functools
import cloudwanderer
from .mocks import generate_mock_session


def patch_resource_collections(collections):
    def decorator_patch_resource_collections(func):
        @functools.wraps(func)
        def wrapper_patch_resource_collections(*args, **kwargs):
            with patch.object(
                cloudwanderer.cloud_wanderer.CloudWandererBoto3Interface,
                'get_resource_collections',
                new=MagicMock(side_effect=lambda service_resource: [
                    collection
                    for collection in collections
                    if service_resource.meta.service_name == collection.meta.service_name
                ])
            ):
                return func(*args, **kwargs)
        return wrapper_patch_resource_collections
    return decorator_patch_resource_collections


def patch_services(services):
    def decorator_patch_services(func):
        @functools.wraps(func)
        def wrapper_patch_services(*args, **kwargs):
            with patch.object(
                cloudwanderer.cloud_wanderer.CloudWandererBoto3Interface,
                'get_all_resource_services',
                new=MagicMock(return_value=[generate_mock_session().resource(service) for service in services])
            ):
                return func(*args, **kwargs)
        return wrapper_patch_services
    return decorator_patch_services
