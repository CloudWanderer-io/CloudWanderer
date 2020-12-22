import logging
import unittest
from unittest.mock import MagicMock, ANY
from moto import mock_ec2, mock_sts, mock_iam, mock_s3
from ..helpers import patch_resource_collections, patch_services, MockStorageConnectorMixin
from ..mocks import (
    add_infra,
    MOCK_COLLECTION_INSTANCES,
    MOCK_COLLECTION_BUCKETS,
    MOCK_COLLECTION_IAM_GROUPS,
    generate_mock_session
)
from cloudwanderer import CloudWanderer


@mock_ec2
@mock_sts
@mock_iam
@mock_s3
class TestCloudWandererWriteResources(unittest.TestCase, MockStorageConnectorMixin):

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

    @patch_services(['ec2', 's3'])
    @patch_resource_collections(collections=[
        MOCK_COLLECTION_INSTANCES, MOCK_COLLECTION_BUCKETS,
        MOCK_COLLECTION_IAM_GROUPS])
    def test_write_resources_in_region_default_region(self):

        self.wanderer.write_resources_in_region()

        self.mock_storage_connector.write_resource.assert_called()
        self.assert_storage_connector_write_resource_called_with(
            region='eu-west-2',
            service='ec2',
            resource_type='instance',
            attributes_dict={
                'vpc_id': ANY,
                'subnet_id': ANY,
                'instance_id': ANY
            }
        )
        self.assert_storage_connector_write_resource_called_with(
            region='eu-west-2',
            service='s3',
            resource_type='bucket',
            attributes_dict={
                'name': 'test-eu-west-2'
            }
        )
        self.assert_storage_connector_write_resource_not_called_with(
            region='us-east-1',
            service='iam',
            resource_type='group',
            attributes_dict={
                'group_name': 'test-group',
                'path': '/'
            }
        )

    @patch_services(['ec2', 's3', 'iam'])
    @patch_resource_collections(collections=[
        MOCK_COLLECTION_INSTANCES, MOCK_COLLECTION_BUCKETS,
        MOCK_COLLECTION_IAM_GROUPS])
    def test_write_resources_in_region_specify_region(self):

        self.wanderer.write_resources_in_region(region_name='us-east-1')

        self.mock_storage_connector.write_resource.assert_called()
        self.assert_storage_connector_write_resource_called_with(
            region='us-east-1',
            service='ec2',
            resource_type='instance',
            attributes_dict={
                'vpc_id': ANY,
                'subnet_id': ANY,
                'instance_id': ANY
            }
        )
        self.assert_storage_connector_write_resource_called_with(
            region='us-east-1',
            service='s3',
            resource_type='bucket',
            attributes_dict={
                'name': 'test-us-east-1'
            }
        )
        self.assert_storage_connector_write_resource_called_with(
            region='us-east-1',
            service='iam',
            resource_type='group',
            attributes_dict={
                'group_name': 'test-group',
                'path': '/'
            }
        )

    @patch_resource_collections(collections=[
        MOCK_COLLECTION_INSTANCES, MOCK_COLLECTION_BUCKETS,
        MOCK_COLLECTION_IAM_GROUPS])
    def test_write_resources_of_service_default_region(self):
        self.wanderer.write_resources_of_service_in_region(service_name='ec2')
        self.wanderer.write_resources_of_service_in_region(service_name='s3')

        self.mock_storage_connector.write_resource.assert_called()
        self.assert_storage_connector_write_resource_called_with(
            region='eu-west-2',
            service='ec2',
            resource_type='instance',
            attributes_dict={
                'vpc_id': ANY,
                'subnet_id': ANY,
                'instance_id': ANY
            }
        )
        self.assert_storage_connector_write_resource_called_with(
            region='eu-west-2',
            service='s3',
            resource_type='bucket',
            attributes_dict={
                'name': 'test-eu-west-2'
            }
        )
        self.assert_storage_connector_write_resource_not_called_with(
            region='us-east-1',
            service='iam',
            resource_type='group',
            attributes_dict={
                'group_name': 'test-group',
                'path': '/'
            }
        )

    @patch_resource_collections(collections=[
        MOCK_COLLECTION_INSTANCES, MOCK_COLLECTION_BUCKETS,
        MOCK_COLLECTION_IAM_GROUPS])
    def test_write_resources_of_service_specify_region(self):
        self.wanderer.write_resources_of_service_in_region(service_name='ec2', region_name='us-east-1')
        self.wanderer.write_resources_of_service_in_region(service_name='s3', region_name='us-east-1')
        self.wanderer.write_resources_of_service_in_region(service_name='iam', region_name='us-east-1')

        self.mock_storage_connector.write_resource.assert_called()
        self.assert_storage_connector_write_resource_called_with(
            region='us-east-1',
            service='ec2',
            resource_type='instance',
            attributes_dict={
                'vpc_id': ANY,
                'subnet_id': ANY,
                'instance_id': ANY
            }
        )
        self.assert_storage_connector_write_resource_called_with(
            region='us-east-1',
            service='s3',
            resource_type='bucket',
            attributes_dict={
                'name': 'test-us-east-1'
            }
        )
        self.assert_storage_connector_write_resource_called_with(
            region='us-east-1',
            service='iam',
            resource_type='group',
            attributes_dict={
                'group_name': 'test-group',
                'path': '/'
            }
        )

    def test_write_resources_of_type_in_region_default_region(self):
        self.wanderer.write_resources_of_type_in_region(service_name='s3', resource_type='bucket')
        self.wanderer.write_resources_of_type_in_region(service_name='ec2', resource_type='instance')
        self.wanderer.write_resources_of_type_in_region(service_name='iam', resource_type='group')

        self.assert_storage_connector_write_resource_called_with(
            region='eu-west-2',
            service='ec2',
            resource_type='instance',
            attributes_dict={
                'vpc_id': ANY,
                'subnet_id': ANY,
                'instance_id': ANY
            }
        )
        self.assert_storage_connector_write_resource_called_with(
            region='eu-west-2',
            service='s3',
            resource_type='bucket',
            attributes_dict={
                'name': 'test-eu-west-2'
            }
        )
        self.assert_storage_connector_write_resource_not_called_with(
            region='us-east-1',
            service='iam',
            resource_type='group',
            attributes_dict={
                'group_name': 'test-group',
                'path': '/'
            }
        )

    @patch_services(['iam'])
    def test_write_resources_of_type_in_region_specify_region(self):
        self.wanderer.write_resources_of_type_in_region(
            service_name='s3', resource_type='bucket', region_name='us-east-1')
        self.wanderer.write_resources_of_type_in_region(
            service_name='ec2', resource_type='instance', region_name='us-east-1')
        self.wanderer.write_resources_of_type_in_region(
            service_name='iam', resource_type='group', region_name='us-east-1')

        self.assert_storage_connector_write_resource_called_with(
            region='us-east-1',
            service='ec2',
            resource_type='instance',
            attributes_dict={
                'vpc_id': ANY,
                'subnet_id': ANY,
                'instance_id': ANY
            }
        )
        self.assert_storage_connector_write_resource_called_with(
            region='us-east-1',
            service='s3',
            resource_type='bucket',
            attributes_dict={
                'name': 'test-us-east-1'
            }
        )
        self.assert_storage_connector_write_resource_called_with(
            region='us-east-1',
            service='iam',
            resource_type='group',
            attributes_dict={
                'group_name': 'test-group',
                'path': '/'
            }
        )
