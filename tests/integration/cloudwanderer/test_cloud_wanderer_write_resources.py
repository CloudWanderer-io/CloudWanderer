import logging
import unittest
from unittest.mock import MagicMock
from moto import mock_ec2, mock_sts, mock_iam
from ..helpers import patch_resource_collections, patch_services
from ..mocks import add_infra, MOCK_COLLECTION_INSTANCES, generate_mock_session
from cloudwanderer import CloudWanderer


@mock_ec2
@mock_sts
@mock_iam
class TestCloudWandererWrite(unittest.TestCase):

    @mock_ec2
    @mock_sts
    @mock_iam
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

    @patch_resource_collections(collections=[MOCK_COLLECTION_INSTANCES])
    def test_write_resources(self):
        self.wanderer.write_resources(service_name='ec2')

        self.mock_storage_connector.write_resource.assert_called_once()
        urn, resource = self.mock_storage_connector.write_resource.call_args_list[0][0]
        assert urn.account_id == '123456789012'
        assert urn.region == 'eu-west-2'
        assert urn.service == 'ec2'
        assert urn.resource_type == 'instance'

        assert set(['VpcId', 'SubnetId', 'InstanceId']).issubset(resource.meta.data.keys())

    @patch_services(['ec2'])
    @patch_resource_collections(collections=[MOCK_COLLECTION_INSTANCES])
    def test_write_all_resources(self):

        self.wanderer.write_all_resources()

        self.mock_storage_connector.write_resource.assert_called_once()
        urn, resource = self.mock_storage_connector.write_resource.call_args_list[0][0]
        assert urn.account_id == '123456789012'
        assert urn.region == 'eu-west-2'
        assert urn.service == 'ec2'
        assert urn.resource_type == 'instance'

        assert set(['VpcId', 'SubnetId', 'InstanceId']).issubset(resource.meta.data.keys())

    @patch_services(['iam'])
    def test_write_all_resources_specify_region(self):

        self.wanderer.write_all_resources(region_name='us-east-1')

        urn, resource = self.mock_storage_connector.write_resource.call_args_list[0][0]
        assert urn.account_id == '123456789012'
        assert urn.region == 'us-east-1'
        assert urn.service == 'iam'
        assert urn.resource_type == 'group'

        assert set(['GroupId', 'GroupName', 'Path']).issubset(resource.meta.data.keys())

    @patch_services(['iam'])
    def test_write_resources_of_type_specify_region(self):
        self.wanderer.write_resources_of_type(
            service_name='iam', resource_type='group', region_name='us-east-1')

        urn, resource = self.mock_storage_connector.write_resource.call_args_list[0][0]
        assert urn.account_id == '123456789012'
        assert urn.region == 'us-east-1'
        assert urn.service == 'iam'
        assert urn.resource_type == 'group'

        assert set(['GroupId', 'GroupName', 'Path']).issubset(resource.meta.data.keys())
