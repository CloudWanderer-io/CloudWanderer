import unittest
from moto import mock_dynamodb2, mock_ec2
from ..mocks import generate_mock_session, add_infra, generate_urn
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
        add_infra()

    def setUp(self):
        self.mock_session = generate_mock_session()
        self.connector = DynamoDbConnector(
            boto3_session=self.mock_session
        )
        self.ec2_instances = list(self.mock_session.resource('ec2').instances.all())
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
