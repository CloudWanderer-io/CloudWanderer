import unittest
from unittest.mock import MagicMock
from ..mocks import add_infra, generate_mock_session
from ..helpers import MockStorageConnectorMixin, setup_moto, get_secondary_attribute_types
from cloudwanderer import CloudWanderer
from cloudwanderer.boto3_interface import CloudWandererBoto3Interface


def expected_service_logs():
    boto3_interface = CloudWandererBoto3Interface()
    supported_services = [
        service.meta.service_name
        for service in boto3_interface.get_all_resource_services()
    ]
    for service_name in supported_services:
        secondary_attribute_resources = set(
            resource_name
            for resource_name, _ in get_secondary_attribute_types(service_name))
        for resource_name in secondary_attribute_resources:
            yield f'INFO:cloudwanderer:Writing all {service_name} {resource_name} secondary attributes in us-east-1'


class TestCloudWandererWriteResourceAttributes(unittest.TestCase, MockStorageConnectorMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enabled_regions = ['eu-west-2', 'us-east-1', 'ap-east-1']
        setup_moto(
            restrict_regions=self.enabled_regions,
        )
        self.mock_session = generate_mock_session()
        add_infra(regions=self.enabled_regions)
        self.expected_service_logs = expected_service_logs()

    def setUp(self):
        self.mock_storage_connector = MagicMock()
        self.wanderer = CloudWanderer(
            storage_connectors=[self.mock_storage_connector],
            boto3_session=generate_mock_session()
        )

    def test_write_secondary_attributes(self):
        self.wanderer.write_secondary_attributes()

        for region_name in self.enabled_regions:
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
        assert sorted(service_logs) == sorted(self.expected_service_logs)

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
