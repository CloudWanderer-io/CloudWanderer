import unittest
from pprint import pprint
import logging
from cloud_wanderer import CloudWanderer
from cloud_wanderer.storage_connectors import DynamoDbConnector


class TestFunctional(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.basicConfig(level='debug')

    def setUp(self):
        self.wanderer = CloudWanderer(storage_connector=DynamoDbConnector(
            endpoint_url='http://localhost:8000'
        ), service_name='ec2')

    def test_write_resources(self):
        self.wanderer.storage_connector.init()
        self.wanderer.write_resources()

    def test_dump(self):
        pprint(self.wanderer.storage_connector.dump())

    def test_read_resource_of_type(self):
        print(list(self.wanderer.read_resource_of_type(service='ec2', resource_type='vpc')))

    def test_read_resource(self):
        vpc = list(self.wanderer.read_resource_of_type(service='ec2', resource_type='vpc'))[0]
        print(self.wanderer.read_resource(urn=vpc.urn))

    def test_read_resource_from_account(self):
        vpc = list(self.wanderer.read_resource_of_type(service='ec2', resource_type='vpc'))[0]
        print([str(x.urn) for x in self.wanderer.read_resource_from_account(vpc.urn.account_id)])
