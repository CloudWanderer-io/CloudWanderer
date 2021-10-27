import pytest

from cloudwanderer.cloud_wanderer_resource import CloudWandererResource
from cloudwanderer.models import Relationship, RelationshipDirection
from cloudwanderer.urn import URN, PartialUrn


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
                resource_id_parts=["test-role", "test-role-policy-1"],
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


@pytest.fixture
def iam_instance_profile():
    return CloudWandererResource(
        urn=URN(
            account_id="111111111111",
            region="us-east-1",
            service="iam",
            resource_type="instance_profile",
            resource_id_parts=["my-test-profile"],
        ),
        resource_data={},
        dependent_resource_urns=[],
        relationships=[
            Relationship(
                partial_urn=PartialUrn(
                    cloud_name="aws",
                    account_id="unknown",
                    region="us-east-1",
                    service="iam",
                    resource_type="role",
                    resource_id_parts=["test-role"],
                ),
                direction=RelationshipDirection.INBOUND,
            )
        ],
    )
