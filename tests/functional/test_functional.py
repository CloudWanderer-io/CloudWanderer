from cloudwanderer.boto3_interface import CloudWandererBoto3Interface
import unittest
import logging
import botocore
import boto3
from cloudwanderer import CloudWanderer
from cloudwanderer.storage_connectors import DynamoDbConnector


class TestFunctional(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.basicConfig(level='debug')

    def setUp(self):
        self.storage_connector = DynamoDbConnector(
            endpoint_url='http://localhost:8000',
            client_args={
                'config': botocore.config.Config(
                    max_pool_connections=100,
                )
            }
        )
        self.storage_connector.init()
        self.wanderer = CloudWanderer(storage_connectors=[self.storage_connector])

    def test_write_resources(self):
        self.wanderer.write_resources_concurrently(
            exclude_resources=['ec2:image', 'ec2:snapshot', 'iam:policy'],
            concurrency=128,
            cloud_interface_generator=lambda: CloudWandererBoto3Interface(boto3_session=boto3.session.Session())
        )

    def test_write_resources_in_region(self):
        self.wanderer.write_resources_in_region(
            region_name='us-east-1', exclude_resources=['ec2:image', 'ec2:snapshot', 'iam:policy'])

    def test_write_custom_resource_definition(self):
        self.wanderer.write_resources_of_service_in_region('lambda', exclude_resources=['images', 'snapshots'])

    def test_read_all(self):
        for x in self.storage_connector.read_all():
            print(x)

    def test_read_resource_of_type(self):
        vpcs = self.storage_connector.read_resources(service='ec2', resource_type='vpc')

        print(list(vpcs))

    def test_read_all_resources_in_account(self):
        vpc = next(self.storage_connector.read_resources(service='ec2', resource_type='vpc'))
        print([str(x.urn) for x in self.storage_connector.read_resources(account_id=vpc.urn.account_id)])

    def test_read_resource_of_type_in_account(self):
        vpc = list(self.storage_connector.read_resources(service='ec2', resource_type='vpc'))[0]
        print([str(x.urn) for x in self.storage_connector.read_resources(
            service='ec2', resource_type='vpc', account_id=vpc.urn.account_id)])

    def test_documentation_resource_example(self):
        storage_connector = self.storage_connector
        resources = storage_connector.read_resources(
            service="ec2",
            resource_type="vpc")
        for resource in resources:
            resource.load()
            print(resource.urn)
            print(resource.cidr_block)
            print(resource.cidr_block_association_set)
            print(resource.dhcp_options_id)
            print(resource.instance_tenancy)
            print(resource.ipv6_cidr_block_association_set)
            print(resource.is_default)
            print(resource.owner_id)
            print(resource.state)
            print(resource.tags)
            print(resource.vpc_id)

    def test_documentation_secondary_attribute_example(self):
        storage_connector = self.storage_connector
        resources = storage_connector.read_resources(
            service="ec2",
            resource_type="vpc")
        for resource in resources:
            resource.get_secondary_attribute(name="vpc_enable_dns_support")

    def test_documentation_subresource_example(self):
        storage_connector = self.storage_connector
        resources = storage_connector.read_resources(
            service="iam",
            resource_type="role")
        for resource in resources:
            resource.load()
            print(resource.urn)
            print(resource.arn)
            print(resource.assume_role_policy_document)
            print(resource.create_date)
            print(resource.description)
            print(resource.max_session_duration)
            print(resource.path)
            print(resource.permissions_boundary)
            print(resource.role_id)
            print(resource.role_last_used)
            print(resource.role_name)
            print(resource.tags)
