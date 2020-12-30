from .mocks import generate_mock_session, add_infra, generate_urn, generate_mock_resource_attribute
from .helpers import mock_services


class StorageWriteTestMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        mock_services()
        self.mock_session = generate_mock_session()

        add_infra(count=100, regions=['eu-west-2'])
        self.ec2_instances = list(self.mock_session.resource('ec2').instances.all())
        self.vpcs = list(self.mock_session.resource('ec2').vpcs.all())

    def test_write_resource_and_attribute(self):
        urn = generate_urn(service='ec2', resource_type='instance', id=self.ec2_instances[0].instance_id)

        self.connector.write_resource(
            urn=urn,
            resource=self.ec2_instances[0]
        )
        self.connector.write_resource_attribute(
            urn=urn,
            attribute_type='vpc_enable_dns_support',
            resource_attribute=generate_mock_resource_attribute({'EnableDnsSupport': {'Value': True}})
        )
        result = self.connector.read_resource(urn=urn)
        assert result.urn == urn
        assert result.instance_type == 'm1.small'
        assert result.placement == {'AvailabilityZone': 'eu-west-2a', 'GroupName': None, 'Tenancy': 'default'}
        assert result.cloudwanderer_metadata.secondary_attributes[0][
            'EnableDnsSupport'] == {
            'Value': True
        }

    def test_write_and_delete(self):
        urn = generate_urn(service='ec2', resource_type='instance', id=self.ec2_instances[0].instance_id)

        self.connector.write_resource(
            urn=urn,
            resource=self.ec2_instances[0]
        )
        result_before_delete = self.connector.read_resource(urn=urn)
        self.connector.delete_resource(urn=urn)
        result_after_delete = self.connector.read_resource(urn=urn)

        assert result_before_delete.urn == urn
        assert result_after_delete is None

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
