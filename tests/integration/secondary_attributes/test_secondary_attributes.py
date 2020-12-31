import unittest
import boto3
from botocore import xform_name
from parameterized import parameterized
from cloudwanderer import CloudWanderer
from ..mocks import add_infra
from ..helpers import setup_moto


def get_secondary_attribute_types(service_name):
    wanderer = CloudWanderer(storage_connectors=[])
    return [
        (xform_name(collection.resource.model.name), xform_name(collection.resource.model.shape))
        for collection in
        wanderer.secondary_attributes_interface.get_service_resource_collections(service_name)
    ]


def generate_params():
    setup_moto(restrict_collections=False)
    services = [
        ('ec2', 'eu-west-2'),
        ('iam', 'us-east-1')
    ]
    for service_name, region_name in services:
        for collection_name, resource_name in get_secondary_attribute_types(service_name):
            yield (
                f"{service_name}-{collection_name}",
                service_name,
                region_name,
                resource_name,
                collection_name
            )


class TestSecondaryAttributes(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        setup_moto(restrict_collections=False)
        add_infra()

    @parameterized.expand(generate_params())
    def test_query_secondary_attributes(self, _, service_name, region_name, resource_name, attribute_name):
        wanderer = CloudWanderer(
            storage_connectors=[],
            boto3_session=boto3.Session(region_name=region_name))
        secondary_attributes = [
            secondary_attribute
            for secondary_attribute in
            wanderer.secondary_attributes_interface.get_resources_of_type(service_name, resource_name, None)
            if attribute_name == xform_name(secondary_attribute.meta.resource_model.name)
        ]
        assert len(secondary_attributes) > 0
        assert secondary_attributes[-1].meta.data
