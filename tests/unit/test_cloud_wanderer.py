import logging
import unittest
from unittest.mock import MagicMock, patch
from .mocks import add_servers, MOCK_COLLECTION
from moto import mock_ec2, mock_sts
import cloudwanderer
from cloudwanderer import CloudWanderer


@patch.dict('os.environ', {'AWS_ACCESS_KEY': '111', 'AWS_DEFAULT_REGION': 'eu-west-2'})
@patch.object(cloudwanderer.cloud_wanderer.CloudWandererBoto3Interface,
              'get_resource_collections',
              return_value=[MOCK_COLLECTION])
@mock_ec2
@mock_sts
class TestCloudWanderer(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.basicConfig(level='INFO')

    @patch.dict('os.environ', {'AWS_ACCESS_KEY': '111', 'AWS_DEFAULT_REGION': 'eu-west-2'})
    def setUp(self):
        self.mock_storage_connector = MagicMock()
        self.wanderer = CloudWanderer(storage_connector=self.mock_storage_connector)
        add_servers()

    def test_write_resources(self, _):
        self.wanderer.write_resources(service_name='ec2')

        self.mock_storage_connector.write_resource.assert_called_once()
        urn, resource = self.mock_storage_connector.write_resource.call_args_list[0][0]
        assert urn.account_id == '123456789012'
        assert urn.region == 'eu-west-2'
        assert urn.service == 'ec2'
        assert urn.resource_type == 'instance'

        assert set(['VpcId', 'SubnetId', 'InstanceId']).issubset(resource.meta.data.keys())
