import pytest

from cloudwanderer.cloud_wanderer_resource import CloudWandererResource
from cloudwanderer.urn import URN


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
