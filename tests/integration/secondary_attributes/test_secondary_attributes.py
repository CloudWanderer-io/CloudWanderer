import unittest
import boto3
from parameterized import parameterized
from cloudwanderer.boto3_interface import CloudWandererBoto3Interface
from ..mocks import add_infra
from ..helpers import get_default_mocker, get_secondary_attribute_types


def generate_params():
    get_default_mocker().start_general_mock(restrict_collections=False)
    services = [
        ('ec2', 'eu-west-2'),
        ('iam', 'us-east-1')
    ]
    for service_name, region_name in services:
        for resource_name, attribute_name in get_secondary_attribute_types(service_name):
            yield (
                f"{service_name}-{resource_name}-{attribute_name}",
                service_name,
                region_name,
                resource_name,
                attribute_name
            )


class TestSecondaryAttributes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        get_default_mocker().start_general_mock()
        add_infra()

    @classmethod
    def tearDownClass(cls):
        get_default_mocker().stop_general_mock

    @parameterized.expand(generate_params())
    def test_query_secondary_attributes(self, _, service_name, region_name, resource_type, attribute_name):
        results = []
        boto3_interface = CloudWandererBoto3Interface(boto3_session=boto3.Session(region_name=region_name))

        resources = boto3_interface.get_resources_of_type(
            service_name=service_name,
            resource_type=resource_type
        )
        for resource in resources:
            for secondary_attribute in resource.cloudwanderer_metadata.secondary_attributes:
                if attribute_name == secondary_attribute.name:
                    results.append(secondary_attribute)

        assert len(results) > 0
        assert dict(results[-1]) != {}
