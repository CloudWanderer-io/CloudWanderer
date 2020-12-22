import logging
import unittest
from unittest.mock import MagicMock
from moto import mock_ec2, mock_sts, mock_iam, mock_s3
from ..mocks import add_infra, generate_mock_session
from cloudwanderer import CloudWanderer


@mock_ec2
@mock_sts
@mock_iam
class TestCloudWandererWriteResourceAttributes(unittest.TestCase):

    @mock_ec2
    @mock_sts
    @mock_iam
    @mock_s3
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

    def test_write_resource_attributes(self):
        self.wanderer.write_resource_attributes('ec2')

        self.mock_storage_connector.write_resource_attribute.assert_called_once()
        call_dict = self.mock_storage_connector.write_resource_attribute.call_args_list[0][1]

        assert call_dict['attribute_type'] == 'vpc_enable_dns_support'
        assert call_dict['urn'].resource_type == 'vpc'
        assert set(['EnableDnsSupport']).issubset(call_dict['resource_attribute'].meta.data.keys())

    def test_write_resource_attributes_with_region(self):
        self.wanderer.write_resource_attributes('ec2', region_name='us-east-1')

        self.mock_storage_connector.write_resource_attribute.assert_called_once()
        call_dict = self.mock_storage_connector.write_resource_attribute.call_args_list[0][1]
        assert call_dict['attribute_type'] == 'vpc_enable_dns_support'
        assert call_dict['urn'].resource_type == 'vpc'
        assert set(['EnableDnsSupport']).issubset(call_dict['resource_attribute'].meta.data.keys())

    def test_write_resource_attributes_ignores_services_out_of_region(self):
        self.wanderer.write_resource_attributes('iam', region_name='eu-west-1')

        self.mock_storage_connector.write_resource_attribute.assert_not_called()

    def test_write_all_resource_attributes(self):
        self.wanderer.write_all_resource_attributes(region_name='eu-west-1')

        self.mock_storage_connector.write_resource_attribute.assert_called()
        call_dict = self.mock_storage_connector.write_resource_attribute.call_args_list[0][1]
        assert call_dict['attribute_type'] == 'vpc_enable_dns_support'
        assert call_dict['urn'].resource_type == 'vpc'
        assert set(['EnableDnsSupport']).issubset(call_dict['resource_attribute'].meta.data.keys())

    def test_write_all_resource_attributes_exclude_resource(self):
        self.wanderer.write_all_resource_attributes(region_name='eu-west-1', exclude_resources=['vpc'])

        self.mock_storage_connector.write_resource_attribute.assert_not_called()

    def test_write_resource_attributes_of_type(self):
        self.wanderer.write_resource_attributes_of_type('ec2', 'vpc')

        self.mock_storage_connector.write_resource_attribute.assert_called()
        call_dict = self.mock_storage_connector.write_resource_attribute.call_args_list[0][1]
        assert call_dict['attribute_type'] == 'vpc_enable_dns_support'
        assert call_dict['urn'].resource_type == 'vpc'
        assert set(['EnableDnsSupport']).issubset(call_dict['resource_attribute'].meta.data.keys())
