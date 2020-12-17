import logging
import unittest
from unittest.mock import MagicMock
from cloudwanderer import CloudWanderer, AwsUrn
from .mocks import generate_mock_session


class TestCloudWandererRead(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.basicConfig(level='INFO')
        self.test_urn = AwsUrn(
            account_id='11111111111',
            region='eu-west-2',
            service='ec2',
            resource_type='vpc',
            resource_id='vpc-11111111'
        )

    def setUp(self):
        self.mock_storage_connector = MagicMock()
        self.wanderer = CloudWanderer(
            storage_connector=self.mock_storage_connector,
            boto3_session=generate_mock_session()
        )

    def test_read_resource_of_type(self):
        self.wanderer.read_resource_of_type(service='ec2', resource_type='vpc')

        self.mock_storage_connector.read_resource_of_type.assert_called_with('ec2', 'vpc')

    def test_read_resource(self):
        self.wanderer.read_resource(urn=self.test_urn)

        self.mock_storage_connector.read_resource.assert_called_with(self.test_urn)

    def test_read_all_resources_in_account(self):
        self.wanderer.read_all_resources_in_account(account_id='111111111111')

        self.mock_storage_connector.read_all_resources_in_account('111111111111')

    def test_read_resource_of_type_in_account(self):
        self.wanderer.read_resource_of_type_in_account(
            service='ec2',
            resource_type='vpc',
            account_id='111111111111'
        )

        self.mock_storage_connector.read_resource_of_type_in_account.assert_called_with('ec2', 'vpc', '111111111111')
