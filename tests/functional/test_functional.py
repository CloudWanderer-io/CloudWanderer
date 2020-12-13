import unittest
import logging
from cloudwanderer import CloudWanderer
from cloudwanderer.storage_connectors import DynamoDbConnector


class TestFunctional(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.basicConfig(level='debug')

    def setUp(self):
        self.wanderer = CloudWanderer(storage_connector=DynamoDbConnector(
            endpoint_url='http://localhost:8000'
        ))

    def test_write_all_resources(self):
        self.wanderer.storage_connector.init()
        self.wanderer.write_all_resources(exclude_resources=['images', 'snapshots'])

    def test_write_custom_resource_definition(self):
        self.wanderer.storage_connector.init()
        self.wanderer.write_resources('lambda', exclude_resources=['images', 'snapshots'])

    def test_read_all(self):
        for x in self.wanderer.storage_connector.read_all():
            print(x.metadata)

    def test_read_resource_of_type(self):
        vpcs = self.wanderer.read_resource_of_type(service='ec2', resource_type='vpc')

        for i, x in enumerate(vpcs):
            print(i, dict(self.wanderer.read_resource(x.urn)))

    def test_read_resource(self):
        vpc = next(self.wanderer.read_resource_of_type(service='ec2', resource_type='vpc'))
        print(self.wanderer.read_resource(urn=vpc.urn))

    def test_read_all_resources_in_account(self):
        vpc = next(self.wanderer.read_resource_of_type(service='ec2', resource_type='vpc'))
        print([str(x.urn) for x in self.wanderer.read_all_resources_in_account(vpc.urn.account_id)])

    def test_read_resource_of_type_in_account(self):
        vpc = list(self.wanderer.read_resource_of_type(service='ec2', resource_type='vpc'))[0]
        print([str(x.urn) for x in self.wanderer.read_resource_of_type_in_account(
            service='ec2', resource_type='vpc', account_id=vpc.urn.account_id)])

    def test_write_resource_attributes(self):
        self.wanderer.write_resource_attributes('ec2')
