import logging
import unittest
from unittest.mock import MagicMock
from ..mocks import add_infra, generate_mock_session, ENABLED_REGIONS
from ..helpers import MockStorageConnectorMixin, setup_moto
from cloudwanderer import CloudWanderer


class TestCloudWandererWriteResourceAttributes(unittest.TestCase, MockStorageConnectorMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.basicConfig(level='INFO')
        setup_moto(restrict_regions=ENABLED_REGIONS)
        add_infra()
        self.mock_storage_connector = MagicMock()
        self.wanderer = CloudWanderer(
            storage_connectors=[self.mock_storage_connector],
            boto3_session=generate_mock_session()
        )
        self.supported_services = [
            service.meta.service_name
            for service in self.wanderer.boto3_interface.get_all_custom_resource_services()
        ]
        self.expected_service_logs = [
            f'INFO:cloudwanderer:Writing all {service} secondary attributes in us-east-1'
            for service in self.supported_services
        ]

    def setUp(self):
        self.mock_storage_connector = MagicMock()
        self.wanderer = CloudWanderer(
            storage_connectors=[self.mock_storage_connector],
            boto3_session=generate_mock_session()
        )

    def test_write_secondary_attributes(self):
        self.wanderer.write_secondary_attributes()

        for region_name in ENABLED_REGIONS:
            self.assert_storage_connector_write_secondary_attribute_called_with(
                region=region_name,
                service='ec2',
                resource_type='vpc',
                response_dict={
                    'EnableDnsSupport': {'Value': True}
                },
                attribute_type='vpc_enable_dns_support'
            )

    def test_write_secondary_attributes_of_service_in_region(self):
        self.wanderer.write_secondary_attributes_of_service_in_region('ec2')

        self.assert_storage_connector_write_secondary_attribute_called_with(
            region='eu-west-2',
            service='ec2',
            resource_type='vpc',
            response_dict={
                'EnableDnsSupport': {'Value': True}
            },
            attribute_type='vpc_enable_dns_support'
        )

    def test_write_secondary_attributes_of_service_in_region_with_region(self):
        self.wanderer.write_secondary_attributes_of_service_in_region('ec2', region_name='us-east-1')

        self.mock_storage_connector.write_secondary_attribute.assert_called_once()
        self.assert_storage_connector_write_secondary_attribute_called_with(
            region='us-east-1',
            service='ec2',
            resource_type='vpc',
            response_dict={
                'EnableDnsSupport': {'Value': True}
            },
            attribute_type='vpc_enable_dns_support'
        )

    def test_write_secondary_attributes_of_service_in_region_ignores_services_out_of_region(self):
        self.wanderer.write_secondary_attributes_of_service_in_region('iam', region_name='eu-west-1')

        self.mock_storage_connector.write_secondary_attribute.assert_not_called()

    def test_write_secondary_attributes_in_region_default_region(self):
        self.wanderer.write_secondary_attributes_in_region()

        self.mock_storage_connector.write_secondary_attribute.assert_called()
        self.assert_storage_connector_write_secondary_attribute_called_with(
            region='eu-west-2',
            service='ec2',
            resource_type='vpc',
            response_dict={
                'EnableDnsSupport': {'Value': True}
            },
            attribute_type='vpc_enable_dns_support'
        )

    def test_write_secondary_attributes_in_region_specify_region(self):
        with self.assertLogs('cloudwanderer', 'INFO') as cm:
            self.wanderer.write_secondary_attributes_in_region(region_name='us-east-1')
        service_logs = [entry for entry in cm.output if 'Writing all' in entry]
        assert service_logs == self.expected_service_logs

        self.mock_storage_connector.write_secondary_attribute.assert_called()
        self.assert_storage_connector_write_secondary_attribute_called_with(
            region='us-east-1',
            service='ec2',
            resource_type='vpc',
            response_dict={
                'EnableDnsSupport': {'Value': True}
            },
            attribute_type='vpc_enable_dns_support'
        )

    def test_write_secondary_attributes_in_region_exclude_resource(self):
        self.wanderer.write_secondary_attributes_in_region(exclude_resources=['vpc'])

        self.mock_storage_connector.write_secondary_attribute.assert_not_called()

    def test_write_secondary_attributes_of_type_in_region_default_region(self):
        self.wanderer.write_secondary_attributes_of_type_in_region('ec2', 'vpc')

        self.mock_storage_connector.write_secondary_attribute.assert_called()
        self.assert_storage_connector_write_secondary_attribute_called_with(
            region='eu-west-2',
            service='ec2',
            resource_type='vpc',
            response_dict={
                'EnableDnsSupport': {'Value': True}
            },
            attribute_type='vpc_enable_dns_support'
        )

    def test_write_secondary_attributes_of_type_in_region_specify_region(self):
        self.wanderer.write_secondary_attributes_of_type_in_region('ec2', 'vpc', region_name='us-east-1')

        self.mock_storage_connector.write_secondary_attribute.assert_called()
        self.assert_storage_connector_write_secondary_attribute_called_with(
            region='us-east-1',
            service='ec2',
            resource_type='vpc',
            response_dict={
                'EnableDnsSupport': {'Value': True}
            },
            attribute_type='vpc_enable_dns_support'
        )
