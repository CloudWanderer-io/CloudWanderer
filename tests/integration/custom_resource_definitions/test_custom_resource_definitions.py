import unittest

from boto3.resources.base import ServiceResource
from boto3.resources.model import Collection

from cloudwanderer.custom_resource_definitions import CustomResourceDefinitions

from ..helpers import DEFAULT_SESSION


class TestCustomResourceDefinitions(unittest.TestCase):
    def setUp(self):
        self.custom_resource_definitions = CustomResourceDefinitions(boto3_session=DEFAULT_SESSION)

    def test_get_valid_resource_types(self):
        result = self.custom_resource_definitions.get_valid_resource_types(
            service_name="iam", resource_types=["instance", "role"]
        )

        assert result == ["role"]

    def test_get_all_service_collectionss(self):
        result = list(self.custom_resource_definitions.get_all_service_collections(service_name="iam"))

        assert len(result) >= 8
        assert all(isinstance(resource_collection, Collection) for resource_collection in result)

    def test_get_all_resource_services(self):
        result = list(self.custom_resource_definitions.get_all_resource_services())

        assert all(isinstance(service, ServiceResource) for service in result)
        assert len(result) >= 13

    def test_resource(self):
        assert len(self.custom_resource_definitions.custom_definitions) > 0
        for service_name in sorted(self.custom_resource_definitions.custom_definitions):
            boto3_service = self.custom_resource_definitions.resource(service_name=service_name)
            assert isinstance(
                boto3_service, ServiceResource
            ), f"{boto3_service} is {type(boto3_service)} but should be ServiceResource"
            service_definition = self.custom_resource_definitions.get_custom_service_definition(service_name)
            for resource_name, resource_definition in service_definition["resources"].items():
                getter = getattr(boto3_service, resource_name)
                try:
                    resource = getter("nonsense_id")
                except ValueError:
                    # boto3 native subresources are not yet supported
                    # see https://github.com/CloudWanderer-io/CloudWanderer/issues/95
                    pass
                assert hasattr(resource, "load"), f"{service_name} {resource_name} does not have a load() method"
