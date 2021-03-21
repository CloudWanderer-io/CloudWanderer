from cloudwanderer.cloud_wanderer_resource import CloudWandererResource, SecondaryAttribute

from .helpers import get_default_mocker
from .mocks import add_infra, generate_mock_session, generate_urn


class StorageWriteTestMixin:
    ec2_instances = None
    vpcs = None

    @classmethod
    def setUpClass(cls):
        mocker = get_default_mocker()
        mocker.start_general_mock()
        cls.mock_session = generate_mock_session()

        add_infra(count=100, regions=["eu-west-2"])
        cls.ec2_instances = [
            CloudWandererResource(
                urn=generate_urn(service="ec2", resource_type="instance", id=instance.instance_id),
                resource_data=instance.meta.data,
            )
            for instance in cls.mock_session.resource("ec2").instances.all()
        ]
        cls.vpcs = [
            CloudWandererResource(
                urn=generate_urn(service="ec2", resource_type="vpc", id=vpc.vpc_id),
                resource_data=vpc.meta.data,
                secondary_attributes=[
                    SecondaryAttribute(name="EnableDnsSupport", **{"EnableDnsSupport": {"Value": True}})
                ],
            )
            for vpc in cls.mock_session.resource("ec2").vpcs.all()
        ]
        cls.role = CloudWandererResource(
            urn=generate_urn(service="iam", resource_type="role", id="test-role"),
            resource_data={},
            secondary_attributes=[],
        )
        cls.role_policy = CloudWandererResource(
            urn=generate_urn(service="iam", resource_type="role_policy", id="test-role/test-policy"),
            parent_urn=cls.role.urn,
            resource_data={},
            secondary_attributes=[],
        )

    @classmethod
    def tearDownClass(cls):
        get_default_mocker().stop_general_mock()

    def test_write_resource_and_attribute(self):

        self.connector.write_resource(resource=self.vpcs[0])
        result = self.connector.read_resource(urn=self.vpcs[0].urn)
        assert result.urn == self.vpcs[0].urn
        assert result.is_default is True
        assert result.cloudwanderer_metadata.secondary_attributes[0]["EnableDnsSupport"] == {"Value": True}

    def test_write_and_delete(self):
        self.connector.write_resource(resource=self.ec2_instances[0])
        result_before_delete = self.connector.read_resource(urn=self.ec2_instances[0].urn)
        self.connector.delete_resource(urn=self.ec2_instances[0].urn)
        result_after_delete = self.connector.read_resource(urn=self.ec2_instances[0].urn)

        assert result_before_delete.urn == self.ec2_instances[0].urn
        assert result_after_delete is None

    def test_write_and_delete_resource_of_type_in_account_region(self):
        for i in range(5):
            self.connector.write_resource(resource=self.ec2_instances[i])

        resource_urns = [
            resource.urn for resource in self.connector.read_resources(service="ec2", resource_type="instance")
        ]

        self.connector.delete_resource_of_type_in_account_region(
            service="ec2",
            resource_type="instance",
            account_id="111111111111",
            region="eu-west-2",
            urns_to_keep=resource_urns[4:],
        )

        remaining_urns = [
            resource.urn for resource in self.connector.read_resources(service="ec2", resource_type="instance")
        ]

        assert remaining_urns == resource_urns[4:]

    def test_delete_subresources_from_resource(self):
        """If we are deleting a parent resource we should delete all its subresources."""
        self.connector.write_resource(resource=self.role)
        self.connector.write_resource(resource=self.role_policy)
        role_before_delete = self.connector.read_resource(urn=self.role.urn)
        role_policy_before_delete = self.connector.read_resource(urn=self.role_policy.urn)

        # Delete the parent and ensure the subresources are also deleted
        self.connector.delete_resource(urn=self.role.urn)
        role_after_delete = self.connector.read_resource(urn=self.role.urn)
        role_policy_after_delete = self.connector.read_resource(urn=self.role_policy.urn)

        assert role_before_delete.urn == self.role.urn
        assert role_policy_before_delete.urn == self.role_policy.urn
        assert role_after_delete is None
        assert role_policy_after_delete is None
