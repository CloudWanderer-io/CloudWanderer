import unittest
from boto3.resources.collection import CollectionManager
from cloud_wanderer import CustomResourceDefinitions
class TestCustomResourceDefinitions(unittest.TestCase):

    def test_default(self):
        factory = CustomResourceDefinitions()
        resources = factory.load_custom_service_definitions()
        for boto3_resource in resources:
            for collection in boto3_resource.meta.resource_model.collections:

                for function in getattr(boto3_resource, collection.name).all():
                    print(function.meta.data)
