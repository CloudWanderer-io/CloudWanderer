import sys
import unittest
from pprint import pprint
import logging

sys.path.insert(0, '..')
from cloud_wanderer.cloud_wanderer import Wanderer, DynamoWriter  # noqa


class TestFunctional(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.basicConfig(level='debug')

    def setUp(self):
        self.wanderer = Wanderer(writer=DynamoWriter(
            endpoint_url='http://localhost:8000'
        ), service_name='ec2')

    def test_default(self):
        self.wanderer.writer.init()
        pprint(self.wanderer.writer.dump())
        self.wanderer.write_resources()
