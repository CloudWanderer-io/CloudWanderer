from .helpers import TestStorageConnectorReadMixin, setup_moto
from .mocks import add_infra, generate_mock_session
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
            storage_connectors=[self.connector]
        )
        self.wanderer._account_id = '111111111111'
        self.wanderer.write_resources()
        self.wanderer._account_id = '222222222222'
        self.wanderer.write_resources()
        self.expected_urns = []
        self.not_expected_urns = []

    def test_no_args(self):
        result = list(self.connector.read_resources())

        for account_id in ['111111111111', '222222222222']:
            self.expected_urns.extend([
                {'account_id': account_id, 'region': 'eu-west-2', 'service': 's3', 'resource_type': 'bucket'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 's3', 'resource_type': 'bucket'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 'ec2', 'resource_type': 'vpc'},
                {'account_id': account_id, 'region': 'eu-west-2', 'service': 'ec2', 'resource_type': 'vpc'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 'iam',
                    'resource_type': 'group', 'resource_id': 'test-group'}
            ])
        self.assert_has_matching_aws_urns(result, self.expected_urns)

    def test_account_id(self):
        result = list(self.connector.read_resources(account_id='111111111111'))

        for account_id in ['111111111111']:
            self.expected_urns.extend([
                {'account_id': account_id, 'region': 'eu-west-2', 'service': 's3', 'resource_type': 'bucket'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 's3', 'resource_type': 'bucket'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 'ec2', 'resource_type': 'vpc'},
                {'account_id': account_id, 'region': 'eu-west-2', 'service': 'ec2', 'resource_type': 'vpc'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 'iam',
                    'resource_type': 'group', 'resource_id': 'test-group'}
            ])
        for account_id in ['222222222222']:
            self.not_expected_urns.extend([
                {'account_id': account_id, 'region': 'eu-west-2', 'service': 's3', 'resource_type': 'bucket'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 's3', 'resource_type': 'bucket'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 'ec2', 'resource_type': 'vpc'},
                {'account_id': account_id, 'region': 'eu-west-2', 'service': 'ec2', 'resource_type': 'vpc'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 'iam',
                    'resource_type': 'group', 'resource_id': 'test-group'}
            ])
        self.assert_has_matching_aws_urns(result, self.expected_urns)
        self.assert_does_not_have_matching_aws_urns(result, self.not_expected_urns)

    def test_region(self):
        result = list(self.connector.read_resources(region_name='eu-west-2'))

        for account_id in ['111111111111', '222222222222']:
            self.expected_urns.extend([
                {'account_id': account_id, 'region': 'eu-west-2', 'service': 's3', 'resource_type': 'bucket'},
                {'account_id': account_id, 'region': 'eu-west-2', 'service': 'ec2', 'resource_type': 'vpc'},
            ])
            self.not_expected_urns.extend([
                {'account_id': account_id, 'region': 'us-east-1', 'service': 's3', 'resource_type': 'bucket'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 'ec2', 'resource_type': 'vpc'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 'iam',
                    'resource_type': 'group', 'resource_id': 'test-group'}
            ])
        self.assert_has_matching_aws_urns(result, self.expected_urns)
        self.assert_does_not_have_matching_aws_urns(result, self.not_expected_urns)

    def test_service(self):
        result = self.connector.read_resources(service='ec2')

        for account_id in ['111111111111', '222222222222']:
            self.expected_urns.extend([
                {'account_id': account_id, 'region': 'eu-west-2', 'service': 'ec2', 'resource_type': 'vpc'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 'ec2', 'resource_type': 'vpc'},
            ])
            self.not_expected_urns.extend([
                {'account_id': account_id, 'region': 'us-east-1', 'service': 's3', 'resource_type': 'bucket'},
                {'account_id': account_id, 'region': 'eu-west-2', 'service': 's3', 'resource_type': 'bucket'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 'iam',
                    'resource_type': 'group', 'resource_id': 'test-group'}
            ])
        self.assert_has_matching_aws_urns(result, self.expected_urns)
        self.assert_does_not_have_matching_aws_urns(result, self.not_expected_urns)

    def test_resource_type(self):
        result = list(self.connector.read_resources(resource_type='bucket'))

        for account_id in ['111111111111', '222222222222']:
            self.expected_urns.extend([
                {'account_id': account_id, 'region': 'us-east-1', 'service': 's3', 'resource_type': 'bucket'},
                {'account_id': account_id, 'region': 'eu-west-2', 'service': 's3', 'resource_type': 'bucket'},
            ])
            self.not_expected_urns.extend([
                {'account_id': account_id, 'region': 'eu-west-2', 'service': 'ec2', 'resource_type': 'vpc'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 'ec2', 'resource_type': 'vpc'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 'iam',
                    'resource_type': 'group', 'resource_id': 'test-group'}
            ])
        self.assert_has_matching_aws_urns(result, self.expected_urns)
        self.assert_does_not_have_matching_aws_urns(result, self.not_expected_urns)

    def test_resource_urn(self):
        result = list(self.connector.read_resources(urn=cloudwanderer.AwsUrn(
            account_id='222222222222',
            region='us-east-1',
            service='iam',
            resource_type='group',
            resource_id='test-group'
        )))

        for account_id in ['111111111111', '222222222222']:
            self.not_expected_urns.extend([
                {'account_id': account_id, 'region': 'eu-west-2', 'service': 'ec2', 'resource_type': 'vpc'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 'ec2', 'resource_type': 'vpc'},
                {'account_id': account_id, 'region': 'us-east-1', 'service': 's3', 'resource_type': 'bucket'},
                {'account_id': account_id, 'region': 'eu-west-2', 'service': 's3', 'resource_type': 'bucket'},
            ])
        self.expected_urns.extend([
            {'account_id': '222222222222', 'region': 'us-east-1', 'service': 'iam',
                'resource_type': 'group', 'resource_id': 'test-group'}
        ])
        self.not_expected_urns.extend([
            {'account_id': '111111111111', 'region': 'us-east-1', 'service': 'iam',
                'resource_type': 'group', 'resource_id': 'test-group'}
        ])
        self.assert_has_matching_aws_urns(result, self.expected_urns)
        self.assert_does_not_have_matching_aws_urns(result, self.not_expected_urns)
