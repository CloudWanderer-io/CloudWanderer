import logging
import unittest
from unittest.mock import MagicMock, patch
from moto import mock_ec2, mock_sts
from .mocks import add_infra, MOCK_COLLECTION_INSTANCES, generate_mock_session
import cloudwanderer
from cloudwanderer import CloudWanderer


@mock_ec2
@mock_sts
class TestCloudWandererWrite(unittest.TestCase):

    @mock_ec2
    @mock_sts
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.basicConfig(level='INFO')
        add_infra()

    def setUp(self):
        self.mock_storage_connector = MagicMock()
        self.wanderer = CloudWanderer(
            storage_connector=self.mock_storage_connector,
            boto3_session=generate_mock_session()
        )

    @patch.object(cloudwanderer.cloud_wanderer.CloudWandererBoto3Interface,
                  'get_resource_collections',
                  new=MagicMock(return_value=[MOCK_COLLECTION_INSTANCES]))
    def test_write_resources(self):
        self.wanderer.write_resources(service_name='ec2')

        self.mock_storage_connector.write_resource.assert_called_once()
        urn, resource = self.mock_storage_connector.write_resource.call_args_list[0][0]
        assert urn.account_id == '123456789012'
        assert urn.region == 'eu-west-2'
        assert urn.service == 'ec2'
        assert urn.resource_type == 'instance'

        assert set(['VpcId', 'SubnetId', 'InstanceId']).issubset(resource.meta.data.keys())

    def test_write_resource_attributes(self):
        self.wanderer.write_resource_attributes('ec2')

        self.mock_storage_connector.write_resource_attribute.assert_called_once()
        call_dict = self.mock_storage_connector.write_resource_attribute.call_args_list[0][1]

        assert call_dict['attribute_type'] == 'vpc_enable_dns_support'
        assert call_dict['urn'].resource_type == 'vpc'
        assert set(['EnableDnsSupport']).issubset(call_dict['resource_attribute'].meta.data.keys())

    @patch.object(
        cloudwanderer.cloud_wanderer.CloudWandererBoto3Interface,
        'get_resource_collections',
        new=MagicMock(return_value=[MOCK_COLLECTION_INSTANCES]))
    def test_write_all_resources(self):

        with patch.object(
            cloudwanderer.cloud_wanderer.CloudWandererBoto3Interface,
            'get_all_resource_services',
                new=MagicMock(return_value=[generate_mock_session().resource('ec2')])):
            self.wanderer.write_all_resources()

        self.mock_storage_connector.write_resource.assert_called_once()
        urn, resource = self.mock_storage_connector.write_resource.call_args_list[0][0]
        assert urn.account_id == '123456789012'
        assert urn.region == 'eu-west-2'
        assert urn.service == 'ec2'
        assert urn.resource_type == 'instance'

        assert set(['VpcId', 'SubnetId', 'InstanceId']).issubset(resource.meta.data.keys())
