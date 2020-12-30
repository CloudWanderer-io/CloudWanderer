from itertools import combinations
import logging
from .helpers import TestStorageConnectorReadMixin, setup_moto
from .mocks import add_infra, generate_mock_session
import cloudwanderer


class StorageReadTestMixin(TestStorageConnectorReadMixin):
    """Class which handles testing the various possible argument combinations."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        setup_moto()
        add_infra(regions=['eu-west-2', 'us-east-1'])
        self.maxDiff = 10000

    def setUp(self):
        self.connector = self.connector_class()
        self.connector.init()
        self.memory_storage_connector = cloudwanderer.storage_connectors.MemoryStorageConnector()
        self.wanderer = cloudwanderer.CloudWanderer(
            boto3_session=generate_mock_session(),
            storage_connectors=[self.connector, self.memory_storage_connector]
        )
        self.wanderer._account_id = '111111111111'
        self.wanderer.write_resources()
        self.wanderer._account_id = '222222222222'
        self.wanderer.write_resources()
        self.expected_urns = []
        self.not_expected_urns = []

    def test_no_args(self):
        try:
            result = list(self.connector.read_resources())
        except self.valid_exceptions:
            return

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
        try:
            result = list(self.connector.read_resources(account_id='111111111111'))
        except self.valid_exceptions as ex:
            logging.info('Received: %s while testing account_id= but was in valid_exceptions', ex)
            return

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
        if not result[0].is_inflated:
            result[0].load()
            assert result[0].is_inflated

    def test_region(self):
        try:
            result = list(self.connector.read_resources(region='eu-west-2'))
        except self.valid_exceptions as ex:
            logging.info('Received: %s while testing region= but was in valid_exceptions', ex)
            return

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
        try:
            result = list(self.connector.read_resources(service='ec2'))
        except self.valid_exceptions as ex:
            logging.info('Received: %s while testing service= but was in valid_exceptions', ex)
            return

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
        try:
            result = list(self.connector.read_resources(resource_type='bucket'))
        except self.valid_exceptions as ex:
            logging.info('Received: %s while testing resource_type= but was in valid_exceptions', ex)
            return

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
        try:
            result = list(self.connector.read_resources(urn=cloudwanderer.AwsUrn(
                account_id='222222222222',
                region='us-east-1',
                service='iam',
                resource_type='group',
                resource_id='test-group'
            )))
        except self.valid_exceptions:
            return

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

    def test_arg_permutations(self):
        """Try all possible combinations of arguments and compare against the memory storage connector's results."""
        if isinstance(self.connector, cloudwanderer.storage_connectors.MemoryStorageConnector):
            logging.info('Skipping test_arg_permutations as we are testing memory storage connector')
        for generated_args in get_inflated_arg_combinations():
            try:
                cut_result = sorted(str(resource.urn) for resource in self.connector.read_resources(**generated_args))
            except self.valid_exceptions as ex:
                logging.info('Received: %s while testing %s but was in valid_exceptions', ex, generated_args)
                continue
            correct_result = sorted(
                str(resource.urn)
                for resource in self.memory_storage_connector.read_resources(**generated_args)
            )

            self.assertListEqual(
                correct_result,
                cut_result,
                f"Returned resources did not match for args: {generated_args}"
            )


def get_arg_combinations():
    args = ('account_id', 'region', 'service', 'resource_type', 'urn')
    for i in range(len(args)):
        yield from combinations(args, i)


def inflate_args(args):
    arg_values = {
        'account_id': '111111111111',
        'region': 'eu-west-2',
        'service': 'ec2',
        'resource_type': 'vpc',
        'urn': 'urn:aws:111111111111:eu-west-2:vpc:vpc-111111111'
    }
    return {
        arg: arg_values[arg]
        for arg in args
    }


def get_inflated_arg_combinations():
    for arg_combination in get_arg_combinations():
        yield inflate_args(arg_combination)
