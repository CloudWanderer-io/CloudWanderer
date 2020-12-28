import os
from .helpers import TestStorageConnectorReadMixin, setup_moto
from unittest.mock import MagicMock
from .mocks import add_infra, generate_mock_session
from moto import mock_sts, mock_s3, mock_iam, mock_ec2
import boto3
import cloudwanderer

class TestStorageRead(TestStorageConnectorReadMixin):
    """Class which handles testing the various possible argument combinations."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        setup_moto()
        add_infra(regions=['eu-west-2', 'us-east-1'])

    def setUp(self):
        self.connector = self.connector_class()
        self.wanderer = cloudwanderer.CloudWanderer(
            boto3_session=generate_mock_session(),
            storage_connector=self.connector
            )
        self.wanderer._account_id = '111111111111'
        self.wanderer.write_resources()
        self.wanderer._account_id = '222222222222'
        self.wanderer.write_resources()
        self.expected_urns = []
    
    def test_no_args(self):
        result = self.connector.read_resources()

        for account_id in ['111111111111', '222222222222']:
            self.expected_urns.extend([
                {'account_id': account_id, 'region': 'eu-west-2', 'service': 's3', 'resource_type': 'bucket'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 's3', 'resource_type': 'bucket'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 'ec2', 'resource_type': 'vpc'},
                {'account_id': account_id, 'region': 'eu-west-2', 'service': 'ec2', 'resource_type': 'vpc'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 'iam', 'resource_type': 'group', 'resource_id': 'test-group'}
            ])
        self.assert_has_matching_aws_urns(result, self.expected_urns)