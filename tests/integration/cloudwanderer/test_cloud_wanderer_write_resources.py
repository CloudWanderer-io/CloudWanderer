import logging
import unittest
from unittest.mock import MagicMock, ANY
from moto import mock_ec2, mock_sts, mock_iam, mock_s3
from ..helpers import patch_resource_collections, patch_services
from ..mocks import add_infra, MOCK_COLLECTION_INSTANCES, MOCK_COLLECTION_BUCKETS, generate_mock_session
from cloudwanderer import CloudWanderer


@mock_ec2
@mock_sts
@mock_iam
@mock_s3
class TestCloudWandererWrite(unittest.TestCase):

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
    @patch_resource_collections(collections=[MOCK_COLLECTION_INSTANCES, MOCK_COLLECTION_BUCKETS])
    def test_write_all_resources_default_region(self):

        self.wanderer.write_all_resources()

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

    @patch_services(['ec2', 's3'])
    @patch_resource_collections(collections=[MOCK_COLLECTION_INSTANCES, MOCK_COLLECTION_BUCKETS])
    def test_write_all_resources_specify_region(self):

        self.wanderer.write_all_resources(region_name='us-east-1')

        self.mock_storage_connector.write_resource.assert_called()
        self.assert_storage_connector_write_resource_called_with(
            region='us-east-1',
            service='s3',
            resource_type='bucket',
            attributes_dict={
                'name': 'test-us-east-1'
            }
        )

    @patch_resource_collections(collections=[MOCK_COLLECTION_INSTANCES])
    def test_write_resources(self):
        self.wanderer.write_resources(service_name='ec2')

        self.mock_storage_connector.write_resource.assert_called_once()
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

    @patch_services(['iam'])
    def test_write_resources_of_type_specify_region(self):
        self.wanderer.write_resources_of_type(
            service_name='iam', resource_type='group', region_name='us-east-1')

        self.assert_storage_connector_write_resource_called_with(
            region='us-east-1',
            service='iam',
            resource_type='group',
            attributes_dict={
                'group_name': 'test-group',
                'path': '/'
            }
        )

    def assert_storage_connector_write_resource_called_with(self, region, service, resource_type, attributes_dict):
        matches = []
        for write_resource_call in self.mock_storage_connector.write_resource.call_args_list:
            urn, resource = write_resource_call[0]
            comparisons = []
            for var in ['region', 'service', 'resource_type']:
                comparisons.append(eval(var) == getattr(urn, var))
            for attr, value in attributes_dict.items():
                try:
                    comparisons.append(getattr(resource, attr) == value)
                except AttributeError:
                    comparisons.append(False)
            if all(comparisons):
              matches.append((urn, resource))
        assert matches
