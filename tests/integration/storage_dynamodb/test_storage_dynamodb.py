import unittest
from unittest.mock import Mock
from moto import mock_dynamodb2, mock_ec2
from ..mocks import generate_mock_session, add_infra, generate_urn, generate_mock_resource_attribute
from cloudwanderer.storage_connectors import DynamoDbConnector


@mock_dynamodb2
@mock_ec2
class TestStorageConnectorDynamoDb(unittest.TestCase):

    def reset_dynamodb_table(self):
        try:
            self.mock_session.resource('dynamodb').Table(name='cloud_wanderer').delete()
        except self.mock_session.client('dynamodb').exceptions.ResourceNotFoundException:
            pass
        finally:
            self.connector.init()

    @mock_ec2
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mock_session = generate_mock_session()
        self.connector = DynamoDbConnector(
            boto3_session=self.mock_session
        )

        add_infra(count=100)
        self.ec2_instances = list(self.mock_session.resource('ec2').instances.all())
        self.vpcs = list(self.mock_session.resource('ec2').vpcs.all())

    def setUp(self):
        self.reset_dynamodb_table()

    def test_write_and_read_resource(self):
        urn = generate_urn(service='ec2', resource_type='instance', id=self.ec2_instances[0].instance_id)

        self.connector.write_resource(
            urn=urn,
            resource=self.ec2_instances[0]
        )
        result = next(self.connector.read_resource(urn=urn))
        result_resource_of_type = next(self.connector.read_resource_of_type('ec2', 'instance'))
        result_all_resources = next(self.connector.read_all_resources_in_account(account_id=urn.account_id))
        result_resource_of_type_in_account = next(self.connector.read_resource_of_type_in_account(
            service='ec2',
            resource_type='instance',
            account_id=urn.account_id
        ))
        result_all_raw = next(self.connector.read_all())

        assert result.urn == urn
        assert result.instance_type == 'm1.small'
        assert result.placement == {'AvailabilityZone': 'eu-west-2a', 'GroupName': None, 'Tenancy': 'default'}
        assert result.urn == result_resource_of_type.urn
        assert result.urn == result_all_resources.urn
        assert result.urn == result_resource_of_type_in_account.urn
        assert result.cloudwanderer_metadata.resource_data['_id'] == result_all_raw['_id']

    def test_write_delete_and_read_resource(self):
        urn = generate_urn(service='ec2', resource_type='instance', id=self.ec2_instances[0].instance_id)

        self.connector.write_resource(
            urn=urn,
            resource=self.ec2_instances[0]
        )
        result_before_delete = next(self.connector.read_resource(urn=urn))
        self.connector.delete_resource(urn=urn)
        result_after_delete = next(self.connector.read_resource(urn=urn), None)

        assert result_before_delete.urn == urn
        assert result_after_delete is None

    def test_write_multiple_delete_type_and_read_resource(self):
        urn = None
        for vpc in self.vpcs:
            urn = generate_urn(service='ec2', resource_type='vpcs', id=vpc.vpc_id)
            self.connector.write_resource(
                urn=urn,
                resource=vpc
            )
            self.connector.write_resource_attribute(
                urn=urn,
                attribute_type='vpc_enable_dns_support',
                resource_attribute=generate_mock_resource_attribute({'EnableDnsSupport': {'Value': True}})
            )
        result_raw_before_delete = list(self.connector.read_all())
        result_before_delete = list(self.connector.read_resource_of_type_in_account(
            service=urn.service,
            resource_type=urn.resource_type,
            account_id=urn.account_id,
        ))
        self.connector.delete_resource_of_type_in_account_region(
            service=urn.service,
            resource_type=urn.resource_type,
            account_id=urn.account_id,
            region=urn.region,
            urns_to_keep=[x.urn for x in result_before_delete[:50]]
        )
        result_raw_after_delete = list(self.connector.read_all())
        result_after_delete = list(self.connector.read_resource_of_type_in_account(
            service=urn.service,
            resource_type=urn.resource_type,
            account_id=urn.account_id,
        ))

        assert len(result_raw_before_delete) == 200
        assert len(result_before_delete) == 100
        assert len(result_after_delete) == 50
        assert len(result_raw_after_delete) == 100
