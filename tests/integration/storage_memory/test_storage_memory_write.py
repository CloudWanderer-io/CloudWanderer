import logging

import pytest
from moto import mock_ec2, mock_iam, mock_sts

from cloudwanderer.cloud_wanderer_resource import CloudWandererResource
from cloudwanderer.storage_connectors import MemoryStorageConnector
from cloudwanderer.urn import URN
from tests.pytest_helpers import create_ec2_instances

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def memory_connector(request):
    connector = MemoryStorageConnector()
    connector.init()
    return connector


def get_inferred_ec2_instances(cloudwanderer_boto3_session):
    return [
        CloudWandererResource(
            urn=URN(
                account_id="111111111111",
                region="eu-west-2",
                service="ec2",
                resource_type="instance",
                resource_id_parts=[instance.instance_id],
            ),
            resource_data=instance.meta.data,
        )
        for instance in cloudwanderer_boto3_session.resource("ec2").instances.all()
    ]


def inferred_ec2_vpcs(cloudwanderer_boto3_session):
    return [
        CloudWandererResource(
            urn=URN(
                account_id="111111111111",
                region="eu-west-2",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=[vpc.vpc_id],
            ),
            resource_data=vpc.meta.data,
        )
        for vpc in cloudwanderer_boto3_session.resource("ec2").vpcs.all()
    ]


@pytest.fixture
def iam_role():
    return CloudWandererResource(
        urn=URN(
            account_id="111111111111",
            region="us-east-1",
            service="iam",
            resource_type="role",
            resource_id_parts=["test-role"],
        ),
        resource_data={"RoleName": "test-role", "InlinePolicyAttachments": [{"PolicyNames": ["test-role"]}]},
        dependent_resource_urns=[
            URN(
                account_id="111111111111",
                region="us-east-1",
                service="iam",
                resource_type="role_policy",
                resource_id_parts=["test-role", "test-role-policy"],
            )
        ],
    )


@pytest.fixture
def iam_role_policies():
    return [
        CloudWandererResource(
            urn=URN(
                account_id="111111111111",
                region="us-east-1",
                service="iam",
                resource_type="role_policy",
                resource_id_parts=["test-role", "test-role-policy-1"],
            ),
            resource_data={},
            parent_urn=URN(
                account_id="111111111111",
                region="us-east-1",
                service="iam",
                resource_type="role",
                resource_id_parts=["test-role"],
            ),
        ),
        CloudWandererResource(
            urn=URN(
                account_id="111111111111",
                region="us-east-1",
                service="iam",
                resource_type="role_policy",
                resource_id_parts=["test-role", "test-role-policy-2"],
            ),
            resource_data={},
            parent_urn=URN(
                account_id="111111111111",
                region="us-east-1",
                service="iam",
                resource_type="role",
                resource_id_parts=["test-role"],
            ),
        ),
    ]


@mock_sts
@mock_iam
def test_write_resource_and_attribute(memory_connector, iam_role):

    memory_connector.write_resource(resource=iam_role)
    result = memory_connector.read_resource(urn=iam_role.urn)

    assert result.urn == iam_role.urn
    assert result.role_name == "test-role"
    logger.info(result.cloudwanderer_metadata.resource_data)
    assert result.inline_policy_attachments == [{"PolicyNames": ["test-role"]}]
    assert result.dependent_resource_urns == [
        URN(
            account_id="111111111111",
            region="us-east-1",
            service="iam",
            resource_type="role_policy",
            resource_id_parts=["test-role", "test-role-policy"],
        )
    ]


@mock_sts
@mock_ec2
def test_write_and_delete_instances(memory_connector, cloudwanderer_boto3_session):
    create_ec2_instances()
    inferred_ec2_instances = get_inferred_ec2_instances(cloudwanderer_boto3_session)
    memory_connector.write_resource(resource=inferred_ec2_instances[0])
    result_before_delete = memory_connector.read_resource(urn=inferred_ec2_instances[0].urn)
    memory_connector.delete_resource(urn=inferred_ec2_instances[0].urn)
    result_after_delete = memory_connector.read_resource(urn=inferred_ec2_instances[0].urn)

    assert result_before_delete.urn == inferred_ec2_instances[0].urn
    assert result_after_delete is None


@mock_sts
@mock_ec2
def test_write_and_delete_resource_of_type_in_account_region(memory_connector, cloudwanderer_boto3_session):
    create_ec2_instances(count=5)
    inferred_ec2_instances = get_inferred_ec2_instances(cloudwanderer_boto3_session)

    for i in range(5):
        memory_connector.write_resource(resource=inferred_ec2_instances[i])

    memory_connector.delete_resource_of_type_in_account_region(
        cloud_name="aws",
        service="ec2",
        resource_type="instance",
        account_id="111111111111",
        region="eu-west-2",
        cutoff=None,
    )

    remaining_urns = [
        resource.urn for resource in memory_connector.read_resources(service="ec2", resource_type="instance")
    ]

    assert remaining_urns == []


def test_delete_subresources_from_resource(memory_connector, iam_role, iam_role_policies):
    """If we are deleting a parent resource we should delete all its subresources."""
    memory_connector.write_resource(resource=iam_role)
    memory_connector.write_resource(resource=iam_role_policies[0])
    memory_connector.write_resource(resource=iam_role_policies[1])
    role_before_delete = memory_connector.read_resource(urn=iam_role.urn)
    role_policy_1_before_delete = memory_connector.read_resource(urn=iam_role_policies[0].urn)
    role_policy_2_before_delete = memory_connector.read_resource(urn=iam_role_policies[1].urn)

    # Delete the parent and ensure the subresources are also deleted
    memory_connector.delete_resource(urn=iam_role.urn)
    role_after_delete = memory_connector.read_resource(urn=iam_role.urn)
    role_policy_1_after_delete = memory_connector.read_resource(urn=iam_role_policies[0].urn)
    role_policy_2_after_delete = memory_connector.read_resource(urn=iam_role_policies[1].urn)

    assert role_before_delete.urn == iam_role.urn
    assert role_policy_1_before_delete.urn == iam_role_policies[0].urn
    assert role_policy_2_before_delete.urn == iam_role_policies[1].urn
    assert role_after_delete is None
    assert role_policy_1_after_delete is None
    assert role_policy_2_after_delete is None
