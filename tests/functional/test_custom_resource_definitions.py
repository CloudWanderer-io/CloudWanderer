import unittest
from cloudwanderer import CustomResourceDefinitions


class TestCustomResourceDefinitions(unittest.TestCase):

    def test_default(self):
        factory = CustomResourceDefinitions()
        resources = factory.load_custom_resource_definitions()
        for service_name, boto3_resource in resources.items():
            for collection in boto3_resource.meta.resource_model.collections:
                for function in getattr(boto3_resource, collection.name).all():
                    print(function.meta.data)
