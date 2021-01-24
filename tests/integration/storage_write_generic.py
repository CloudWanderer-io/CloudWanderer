from .mocks import generate_mock_session, add_infra, generate_urn
from .helpers import get_default_mocker
from cloudwanderer.cloud_wanderer_resource import CloudWandererResource, SecondaryAttribute


class StorageWriteTestMixin:
    ec2_instances = None
    vpcs = None

    @classmethod
    def setUpClass(cls):
        mocker = get_default_mocker()
        mocker.start_general_mock()
        cls.mock_session = generate_mock_session()

        add_infra(count=100, regions=['eu-west-2'])
        cls.ec2_instances = [
            CloudWandererResource(
                urn=generate_urn(service='ec2', resource_type='instance', id=instance.instance_id),
                resource_data=instance.meta.data
            )
            for instance in cls.mock_session.resource('ec2').instances.all()
        ]
        cls.vpcs = [
            CloudWandererResource(
                urn=generate_urn(service='ec2', resource_type='vpc', id=vpc.vpc_id),
                resource_data=vpc.meta.data,
                secondary_attributes=[
                    SecondaryAttribute(
                        attribute_name='EnableDnsSupport',
                        **{'EnableDnsSupport': {'Value': True}}
                    )
                ]
            )
            for vpc in cls.mock_session.resource('ec2').vpcs.all()
        ]

    @classmethod
    def tearDownClass(cls):
        get_default_mocker().stop_general_mock()

    def test_write_resource_and_attribute(self):

        self.connector.write_resource(
            resource=self.vpcs[0]
        )
        result = self.connector.read_resource(urn=self.vpcs[0].urn)
        assert result.urn == self.vpcs[0].urn
        assert result.is_default is True
        assert result.cloudwanderer_metadata.secondary_attributes[0][
            'EnableDnsSupport'] == {
            'Value': True
        }

    def test_write_and_delete(self):
        self.connector.write_resource(
            resource=self.ec2_instances[0]
        )
        result_before_delete = self.connector.read_resource(urn=self.ec2_instances[0].urn)
        self.connector.delete_resource(urn=self.ec2_instances[0].urn)
        result_after_delete = self.connector.read_resource(urn=self.ec2_instances[0].urn)

        assert result_before_delete.urn == self.ec2_instances[0].urn
        assert result_after_delete is None

    def test_write_and_delete_resource_of_type_in_account_region(self):
        for i in range(5):
            self.connector.write_resource(
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
