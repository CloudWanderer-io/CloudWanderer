from cloudwanderer.cloud_wanderer_resource import CloudWandererResource
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
        self.mock_session = generate_mock_session()
        add_infra(count=100, regions=['eu-west-2'])
        self.ec2_instances = list(self.mock_session.resource('ec2').instances.all())
        self.vpcs = list(self.mock_session.resource('ec2').vpcs.all())

    def setUp(self):
        self.connector = MemoryStorageConnector()

    def test_write_and_read_resource(self):
        urn = generate_urn(service='ec2', resource_type='instance', id=self.ec2_instances[0].instance_id)

        self.connector.write_resource(
            urn=urn,
            resource=self.ec2_instances[0]
        )
        resource = self.connector.read_resource(urn=urn)

        self.assertIsInstance(resource, CloudWandererResource)
        assert resource.urn.region == 'eu-west-2'
        assert resource.urn.account_id == '111111111111'
        assert resource.urn.resource_type == 'instance'
        assert resource.instance_type == 'm1.small'

    def test_write_and_read_resources_of_type_in_account(self):
        urn = generate_urn(service='ec2', resource_type='instance', id=self.ec2_instances[0].instance_id)

        self.connector.write_resource(
            urn=urn,
            resource=self.ec2_instances[0]
        )
        resource = next(self.connector.read_resources(
            account_id='111111111111',
            service='ec2',
            resource_type='instance'
        ))
        self.assertIsInstance(resource, CloudWandererResource)
        assert resource.urn.region == 'eu-west-2'
        assert resource.urn.resource_type == 'instance'
        self.assertRaises(AttributeError, getattr, resource, 'instance_type')
        resource.load()
        assert resource.instance_type == 'm1.small'

    def test_write_and_read_resource_of_type(self):
        for i in range(5):
            self.connector.write_resource(
                urn=generate_urn(service='ec2', resource_type='instance', id=self.ec2_instances[i].instance_id),
                resource=self.ec2_instances[i]
            )

        resources = self.connector.read_resources(
            service='ec2',
            resource_type='instance'
        )

        for i in range(5):
            resource = next(resources)
            self.assertIsInstance(resource, CloudWandererResource)
            assert resource.urn.region == 'eu-west-2'
            assert resource.urn.resource_type == 'instance'
            self.assertRaises(AttributeError, getattr, resource, 'instance_type')
            resource.load()
            assert resource.instance_type == 'm1.small'

    def test_write_and_read_all_resources_in_account(self):
        self.connector.write_resource(
            urn=generate_urn(service='ec2', resource_type='instance', id=self.ec2_instances[0].instance_id),
            resource=self.ec2_instances[0]
        )
        self.connector.write_resource(
            urn=generate_urn(service='ec2', resource_type='vpc', id=self.vpcs[0].vpc_id),
            resource=self.vpcs[0]
        )

        resources = self.connector.read_resources(
            account_id='111111111111'
        )

        instance = next(resources)
        self.assertIsInstance(instance, CloudWandererResource)
        assert instance.urn.region == 'eu-west-2'
        assert instance.urn.resource_type == 'instance'
        self.assertRaises(AttributeError, getattr, instance, 'instance_type')
        instance.load()
        assert instance.instance_type == 'm1.small'

        vpc = next(resources)
        self.assertIsInstance(instance, CloudWandererResource)
        assert vpc.urn.region == 'eu-west-2'
        assert vpc.urn.resource_type == 'vpc'
        self.assertRaises(AttributeError, getattr, vpc, 'cidr_block')
        vpc.load()
        assert vpc.cidr_block == '172.31.0.0/16'

    def test_write_and_read_all(self):
        self.connector.write_resource(
            urn=generate_urn(service='ec2', resource_type='instance', id=self.ec2_instances[0].instance_id),
            resource=self.ec2_instances[0]
        )
        self.connector.write_resource(
            urn=generate_urn(service='ec2', resource_type='vpc', id=self.vpcs[0].vpc_id),
            resource=self.vpcs[0]
        )

        resources = self.connector.read_all()

        instance = next(resources)
        self.assertIn('urn:aws:111111111111:eu-west-2:ec2:instance:i-', instance['urn'])
        assert instance['attr'] == 'BaseResource'
        vpc = next(resources)
        self.assertIn('urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-', vpc['urn'])

    def test_write_and_delete(self):
        self.connector.write_resource(
            urn=generate_urn(service='ec2', resource_type='instance', id=self.ec2_instances[0].instance_id),
            resource=self.ec2_instances[0]
        )

        instance = next(self.connector.read_resources(service='ec2', resource_type='instance'))
        self.assertIsInstance(instance, CloudWandererResource)

        self.connector.delete_resource(urn=instance.urn)
        self.connector.delete_resource(urn=instance.urn)

        no_resources = self.connector.read_resources(service='ec2', resource_type='instance')
        self.assertRaises(StopIteration, next, no_resources)

        non_resource = self.connector.read_resource(urn=instance.urn)
        assert non_resource is None

    def test_write_and_delete_resource_of_type_in_account_region(self):
        for i in range(5):
            self.connector.write_resource(
                urn=generate_urn(service='ec2', resource_type='instance', id=self.ec2_instances[i].instance_id),
                resource=self.ec2_instances[i]
            )

        resource_urns = [
            resource.urn for resource in
            self.connector.read_resources(
                service='ec2',
                resource_type='instance'
            )
        ]

        self.connector.delete_resource_of_type_in_account_region(
            service='ec2',
            resource_type='instance',
            account_id='111111111111',
            region='eu-west-2',
            urns_to_keep=resource_urns[4:]
        )

        remaining_urns = [
            resource.urn for resource in
            self.connector.read_resources(service='ec2', resource_type='instance')
        ]

        assert remaining_urns == resource_urns[4:]
