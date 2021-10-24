from moto import mock_ec2, mock_iam, mock_s3, mock_sts

from cloudwanderer.cloud_wanderer_resource import URN, CloudWandererResource

from ..helpers import DEFAULT_SESSION
from ..pytest_helpers import create_ec2_instances, create_iam_role, create_s3_buckets
from .mocks import generate_urn


class StorageWriteTestMixin:
    ec2_instances = None
    vpcs = None

    @classmethod
    def setUpClass(cls):
        cls.mocks = [
            mock_sts().start(),
            mock_ec2().start(),
            mock_s3().start(),
            mock_iam().start(),
        ]
        create_ec2_instances()
        create_iam_role()
        create_s3_buckets()
        cls.maxDiff = 10000

        cls.ec2_instances = [
            CloudWandererResource(
                urn=generate_urn(service="ec2", resource_type="instance", resource_id_parts=[instance.instance_id]),
                resource_data=instance.meta.data,
            )
            for instance in DEFAULT_SESSION.resource("ec2").instances.all()
        ]
        cls.vpcs = [
            CloudWandererResource(
                urn=generate_urn(service="ec2", resource_type="vpc", resource_id_parts=[vpc.vpc_id]),
                resource_data=vpc.meta.data,
            )
            for vpc in DEFAULT_SESSION.resource("ec2").vpcs.all()
        ]
        cls.role = CloudWandererResource(
            urn=generate_urn(service="iam", resource_type="role", resource_id_parts=["test-role"]),
            resource_data={"RoleName": "test-role"},
            dependent_resource_urns=[
                generate_urn(
                    service="iam", resource_type="role_policy", resource_id_parts=["test-role", "test-role-policy"]
                )
            ],
        )
        cls.role_policy_1 = CloudWandererResource(
            urn=generate_urn(
                service="iam", resource_type="role_policy", resource_id_parts=["test-role", "test-role-policy-1"]
            ),
            resource_data={},
        )
        cls.role_policy_2 = CloudWandererResource(
            urn=generate_urn(
                service="iam", resource_type="role_policy", resource_id_parts=["test-role", "test-role-policy-2"]
            ),
            resource_data={},
        )

    @classmethod
    def tearDownClass(cls):
        for mock in cls.mocks:
            mock.stop()

    def test_write_resource_and_attribute(self):

        self.connector.write_resource(resource=self.role)
        result = self.connector.read_resource(urn=self.role.urn)
        result.load()
        assert result.urn == self.role.urn
        assert result.role_name == "test-role"
        assert result.role_inline_policy_attachments == [{"PolicyNames": ["test-role"]}]
        assert result.dependent_resource_urns == [
            URN(
                account_id="111111111111",
                region="eu-west-2",
                service="iam",
                resource_type="role_policy",
                resource_id_parts=["test-role", "test-role-policy"],
            )
        ]

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
        self.connector.write_resource(resource=self.role_policy_1)
        self.connector.write_resource(resource=self.role_policy_2)
        role_before_delete = self.connector.read_resource(urn=self.role.urn)
        role_policy_1_before_delete = self.connector.read_resource(urn=self.role_policy_1.urn)
        role_policy_2_before_delete = self.connector.read_resource(urn=self.role_policy_2.urn)

        # Delete the parent and ensure the subresources are also deleted
        self.connector.delete_resource(urn=self.role.urn)
        role_after_delete = self.connector.read_resource(urn=self.role.urn)
        role_policy_1_after_delete = self.connector.read_resource(urn=self.role_policy_1.urn)
        role_policy_2_after_delete = self.connector.read_resource(urn=self.role_policy_2.urn)

        assert role_before_delete.urn == self.role.urn
        assert role_policy_1_before_delete.urn == self.role_policy_1.urn
        assert role_policy_2_before_delete.urn == self.role_policy_2.urn
        assert role_after_delete is None
        assert role_policy_1_after_delete is None
        assert role_policy_2_after_delete is None
