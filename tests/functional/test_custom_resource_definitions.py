import unittest
from cloudwanderer import CustomResourceDefinitions


class TestCustomResourceDefinitions(unittest.TestCase):

    def test_default(self):
        factory = CustomResourceDefinitions()
        for service_name in factory.definitions:
            boto3_resource = factory.resource(service_name=service_name)
            for collection in boto3_resource.meta.resource_model.collections:
                for function in getattr(boto3_resource, collection.name).all():
                    print(function.meta.data)
