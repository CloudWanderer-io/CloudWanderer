from cloudwanderer.cloud_wanderer import CloudWandererResource
import unittest
from cloudwanderer.storage_connectors.memory import MemoryStorageConnector
from moto import mock_ec2, mock_s3, mock_iam
from ..mocks import add_infra, generate_mock_session, generate_urn

@mock_ec2
@mock_s3
@mock_iam
class TestStorageMemory(unittest.TestCase):

    @mock_ec2
    @mock_s3
    @mock_iam
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connector = MemoryStorageConnector()
        self.mock_session = generate_mock_session()
        add_infra(count=100, regions=['eu-west-2'])
        self.ec2_instances = list(self.mock_session.resource('ec2').instances.all())
        self.vpcs = list(self.mock_session.resource('ec2').vpcs.all())

    def test_write_and_read_resource(self):
        urn = generate_urn(service='ec2', resource_type='instance', id=self.ec2_instances[0].instance_id)

        self.connector.write_resource(
            urn=urn,
            resource=self.ec2_instances[0]
        )
        resource = next(self.connector.read_resource(urn=urn))
        self.assertIsInstance(resource, CloudWandererResource)
        assert resource.urn.region == 'eu-west-2'
        assert resource.urn.resource_type == 'instance'
        assert resource.instance_type == 'm1.small'
