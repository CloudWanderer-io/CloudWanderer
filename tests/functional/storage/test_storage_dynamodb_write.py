import logging
import platform

import boto3
import pytest
from moto import mock_ec2, mock_iam, mock_sts

from cloudwanderer.storage_connectors.dynamodb import DynamoDbConnector
from cloudwanderer.urn import URN

from ...pytest_helpers import create_ec2_instances, get_inferred_ec2_instances

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def dynamodb_connnector(request):
    # Take advantage of the fact that dynamodb local creates a separate db instance for each access key
    # to allow github action tests to run multiple python version tests in parallel.
    aws_access_key_id = platform.python_version()
    connector = DynamoDbConnector(
        boto3_session=boto3.Session(
            aws_access_key_id=aws_access_key_id, aws_secret_access_key="1", region_name="eu-west-1"
        ),
        endpoint_url="http://localhost:8000",
    )
    connector.init()

    yield connector
    logger.info("Deleting dynamodb")
    dynamodb = boto3.resource(
        "dynamodb",
        endpoint_url="http://localhost:8000",
        region_name="eu-west-1",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key="1",
    )
    table = dynamodb.Table(
        "cloud_wanderer",
    )
    table.delete()


@mock_sts
@mock_iam
def test_write_resource_and_attribute(dynamodb_connnector, iam_role):

    dynamodb_connnector.write_resource(resource=iam_role)
    result = dynamodb_connnector.read_resource(urn=iam_role.urn)

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
            resource_id_parts=["test-role", "test-role-policy-1"],
        )
    ]


@mock_sts
@mock_ec2
def test_write_and_delete_instances(dynamodb_connnector, cloudwanderer_boto3_session):
    create_ec2_instances()
    inferred_ec2_instances = get_inferred_ec2_instances(cloudwanderer_boto3_session)
    dynamodb_connnector.write_resource(resource=inferred_ec2_instances[0])
    result_before_delete = dynamodb_connnector.read_resource(urn=inferred_ec2_instances[0].urn)
    dynamodb_connnector.delete_resource(urn=inferred_ec2_instances[0].urn)
    result_after_delete = dynamodb_connnector.read_resource(urn=inferred_ec2_instances[0].urn)

    assert result_before_delete.urn == inferred_ec2_instances[0].urn
    assert result_after_delete is None


@mock_sts
@mock_ec2
def test_write_and_delete_resource_of_type_in_account_region(dynamodb_connnector, cloudwanderer_boto3_session):
    create_ec2_instances(count=5)
    inferred_ec2_instances = get_inferred_ec2_instances(cloudwanderer_boto3_session)

    for i in range(5):
        dynamodb_connnector.write_resource(resource=inferred_ec2_instances[i])

    dynamodb_connnector.delete_resource_of_type_in_account_region(
        cloud_name="aws",
        service="ec2",
        resource_type="instance",
        account_id="111111111111",
        region="eu-west-2",
        cutoff=None,
    )

    remaining_urns = [
        resource.urn for resource in dynamodb_connnector.read_resources(service="ec2", resource_type="instance")
    ]

    assert remaining_urns == []


def test_delete_subresources_from_resource(dynamodb_connnector, iam_role, iam_role_policies):
    """If we are deleting a parent resource we should delete all its subresources."""
    dynamodb_connnector.write_resource(resource=iam_role)
    dynamodb_connnector.write_resource(resource=iam_role_policies[0])
    dynamodb_connnector.write_resource(resource=iam_role_policies[1])
    role_before_delete = dynamodb_connnector.read_resource(urn=iam_role.urn)
    role_policy_1_before_delete = dynamodb_connnector.read_resource(urn=iam_role_policies[0].urn)
    role_policy_2_before_delete = dynamodb_connnector.read_resource(urn=iam_role_policies[1].urn)

    # Delete the parent and ensure the subresources are also deleted
    dynamodb_connnector.delete_resource(urn=iam_role.urn)
    role_after_delete = dynamodb_connnector.read_resource(urn=iam_role.urn)
    role_policy_1_after_delete = dynamodb_connnector.read_resource(urn=iam_role_policies[0].urn)
    role_policy_2_after_delete = dynamodb_connnector.read_resource(urn=iam_role_policies[1].urn)

    assert role_before_delete.urn == iam_role.urn
    assert role_policy_1_before_delete.urn == iam_role_policies[0].urn
    assert role_policy_2_before_delete.urn == iam_role_policies[1].urn
    assert role_after_delete is None
    assert role_policy_1_after_delete is None
    assert role_policy_2_after_delete is None
