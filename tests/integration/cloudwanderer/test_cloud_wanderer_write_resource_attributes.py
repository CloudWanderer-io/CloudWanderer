import logging
import unittest
from unittest.mock import MagicMock
from moto import mock_ec2, mock_sts, mock_iam, mock_s3
from ..mocks import add_infra, generate_mock_session
from ..helpers import MockStorageConnectorMixin
from cloudwanderer import CloudWanderer


@mock_ec2
@mock_sts
@mock_iam
class TestCloudWandererWriteResourceAttributes(unittest.TestCase, MockStorageConnectorMixin):

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

    def test_write_resource_attributes_of_service_in_region_attributes(self):
        self.wanderer.write_resource_attributes_of_service_in_region('ec2')

        self.assert_storage_connector_write_resource_attribute_called_with(
            region='eu-west-2',
            service='ec2',
            resource_type='vpc',
            response_dict={
                'EnableDnsSupport': {'Value': True}
            },
            attribute_type='vpc_enable_dns_support'
        )

    def test_write_resource_attributes_of_service_in_region_with_region(self):
        self.wanderer.write_resource_attributes_of_service_in_region('ec2', region_name='us-east-1')

        self.mock_storage_connector.write_resource_attribute.assert_called_once()
        self.assert_storage_connector_write_resource_attribute_called_with(
            region='us-east-1',
            service='ec2',
            resource_type='vpc',
            response_dict={
                'EnableDnsSupport': {'Value': True}
            },
            attribute_type='vpc_enable_dns_support'
        )

    def test_write_resource_attributes_of_service_in_region_ignores_services_out_of_region(self):
        self.wanderer.write_resource_attributes_of_service_in_region('iam', region_name='eu-west-1')

        self.mock_storage_connector.write_resource_attribute.assert_not_called()

    def test_write_resource_attributes_in_region_default_region(self):
        self.wanderer.write_resource_attributes_in_region()

        self.mock_storage_connector.write_resource_attribute.assert_called()
        self.assert_storage_connector_write_resource_attribute_called_with(
            region='eu-west-2',
            service='ec2',
            resource_type='vpc',
            response_dict={
                'EnableDnsSupport': {'Value': True}
            },
            attribute_type='vpc_enable_dns_support'
        )

    def test_write_resource_attributes_in_region_specify_region(self):
        self.wanderer.write_resource_attributes_in_region(region_name='us-east-1')

        self.mock_storage_connector.write_resource_attribute.assert_called()
        self.assert_storage_connector_write_resource_attribute_called_with(
            region='us-east-1',
            service='ec2',
            resource_type='vpc',
            response_dict={
                'EnableDnsSupport': {'Value': True}
            },
            attribute_type='vpc_enable_dns_support'
        )

    def test_write_resource_attributes_in_region_exclude_resource(self):
        self.wanderer.write_resource_attributes_in_region(exclude_resources=['vpc'])

        self.mock_storage_connector.write_resource_attribute.assert_not_called()

    def test_write_resource_attributes_of_type_in_region_default_region(self):
        self.wanderer.write_resource_attributes_of_type_in_region('ec2', 'vpc')

        self.mock_storage_connector.write_resource_attribute.assert_called()
        self.assert_storage_connector_write_resource_attribute_called_with(
            region='eu-west-2',
            service='ec2',
            resource_type='vpc',
            response_dict={
                'EnableDnsSupport': {'Value': True}
            },
            attribute_type='vpc_enable_dns_support'
        )

    def test_write_resource_attributes_of_type_in_region_specify_region(self):
        self.wanderer.write_resource_attributes_of_type_in_region('ec2', 'vpc', region_name='us-east-1')

        self.mock_storage_connector.write_resource_attribute.assert_called()
        self.assert_storage_connector_write_resource_attribute_called_with(
            region='us-east-1',
            service='ec2',
            resource_type='vpc',
            response_dict={
                'EnableDnsSupport': {'Value': True}
            },
            attribute_type='vpc_enable_dns_support'
        )
