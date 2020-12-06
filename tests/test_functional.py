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
