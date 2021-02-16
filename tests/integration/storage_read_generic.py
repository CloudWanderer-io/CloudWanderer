import logging
from itertools import combinations
from time import sleep
from unittest.mock import ANY, patch

import cloudwanderer
from cloudwanderer.cloud_wanderer_resource import SecondaryAttribute

from .helpers import GenericAssertionHelpers, TestStorageConnectorReadMixin, get_default_mocker
from .mocks import add_infra, generate_mock_session


class StorageReadTestMixin(TestStorageConnectorReadMixin, GenericAssertionHelpers):
    """Class which handles testing the various possible argument combinations."""

    @classmethod
    def setUpClass(cls):
        get_default_mocker().start_general_mock()
        generate_mock_session()
        add_infra(regions=['eu-west-2', 'us-east-1'])
        cls.maxDiff = 10000

    @classmethod
    def tearDownClass(cls):
        get_default_mocker().stop_general_mock()

    def setUp(self):
        self.connector = self.connector_class()
        self.connector.init()
        self.memory_storage_connector = cloudwanderer.storage_connectors.MemoryStorageConnector()
        with patch('moto.sts.responses.ACCOUNT_ID', new='111111111111'):
            self.wanderer = cloudwanderer.CloudWanderer(
                storage_connectors=[self.connector, self.memory_storage_connector]
            )
            self.wanderer.write_resources()
        with patch('moto.sts.responses.ACCOUNT_ID', new='222222222222'):
            self.wanderer = cloudwanderer.CloudWanderer(
                storage_connectors=[self.connector, self.memory_storage_connector]
            )
            self.wanderer.write_resources()
        self.expected_urns = []
        self.not_expected_urns = []
        # Occasionally moto needs a second to finish writing.
        sleep(0.1)

    def test_no_args(self):
        try:
            result = list(self.connector.read_resources())
        except self.valid_exceptions:
            return

        self.assert_secondary_attributes(
            result,
            {'role_inline_policy_attachments', 'role_managed_policy_attachments', 'vpc_enable_dns_support'},
            [
                {'VpcId': ANY, 'EnableDnsSupport': {'Value': True}},
                {'PolicyNames': ['test-role-policy'], 'IsTruncated': False},
                {'AttachedPolicies': [{
                    'PolicyName': 'APIGatewayServiceRolePolicy',
                    'PolicyArn': 'arn:aws:iam::aws:policy/aws-service-role/APIGatewayServiceRolePolicy'
                }], 'IsTruncated': False}
            ],
        )

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

        self.assert_secondary_attributes(
            result,
            {'role_inline_policy_attachments', 'role_managed_policy_attachments', 'vpc_enable_dns_support'},
            [
                {'VpcId': ANY, 'EnableDnsSupport': {'Value': True}},
                {'PolicyNames': ['test-role-policy'], 'IsTruncated': False},
                {'AttachedPolicies': [{
                    'PolicyName': 'APIGatewayServiceRolePolicy',
                    'PolicyArn': 'arn:aws:iam::aws:policy/aws-service-role/APIGatewayServiceRolePolicy'
                }], 'IsTruncated': False}
            ],
        )

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
        self.assert_secondary_attributes(
            result,
            {'vpc_enable_dns_support'},
            [{'VpcId': ANY, 'EnableDnsSupport': {'Value': True}}, ],
        )

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
        self.assert_secondary_attributes(
            result,
            {
                'vpc_enable_dns_support'
            },
            [{'VpcId': ANY, 'EnableDnsSupport': {'Value': True}}],
        )

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

        self.assert_secondary_attributes(
            result,
            {},
            [],
        )

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

        self.assert_secondary_attributes(
            result,
            {},
            [],
        )

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

    def assert_secondary_attributes(self, result, expected_attribute_names, expected_attribute_dicts):
        """Assert that the list of resources provided contains the expected attributes."""
        for resource in result:
            resource.load()

        secondary_attributes = self.get_secondary_attributes_from_resources(result)
        assert set(expected_attribute_names).issubset(x.name for x in secondary_attributes)
        self.assert_dictionary_overlap(
            secondary_attributes,
            expected_attribute_dicts
        )
        assert all([isinstance(secondary_attribute, SecondaryAttribute)
                    for secondary_attribute in secondary_attributes])


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
