from unittest.mock import ANY, MagicMock
from cloudwanderer.aws_interface import CloudWandererAWSInterface
from cloudwanderer.cloud_wanderer_resource import CloudWandererResource
from pytest import fixture

from cloudwanderer.urn import URN


@fixture
def aws_interface_vpc() -> CloudWandererAWSInterface:
    mock_cloudwanderer_boto3_session = MagicMock(
        **{
            "available_services": ["ec2"],
            "enabled_regions": ["us-east-1", "eu-west-1"],
            "resource.return_value": MagicMock(**{"resource_types": ["vpc"], "collection.return_value": [MagicMock()]}),
            "account_id": "111111111111",
        }
    )
    return CloudWandererAWSInterface(cloudwanderer_boto3_session=mock_cloudwanderer_boto3_session)


@fixture
def aws_interface_role(cloudwanderer_dependent_urn, cloudwanderer_resource_urn) -> CloudWandererAWSInterface:
    dependent_resource = MagicMock(**{"get_urn.return_value": cloudwanderer_dependent_urn})
    resource = MagicMock(
        **{
            "collection.return_value": [dependent_resource],
            "dependent_resource_types": ["role_policy"],
            "get_urn.return_value": cloudwanderer_resource_urn,
        }
    )

    service = MagicMock(**{"resource.return_value": resource})

    mock_cloudwanderer_boto3_session = MagicMock(
        **{
            "available_services": ["iam"],
            "enabled_regions": ["us-east-1", "eu-west-1"],
            "resource.return_value": service,
            "account_id": "111111111111",
        }
    )
    return CloudWandererAWSInterface(cloudwanderer_boto3_session=mock_cloudwanderer_boto3_session)


@fixture
def cloudwanderer_dependent_urn() -> URN:
    return URN(
        account_id="111111111111",
        region="us-east-1",
        service="iam",
        resource_type="role_policy",
        resource_id_parts=["test-role", "test-policy"],
    )


@fixture
def cloudwanderer_resource_urn() -> URN:
    return URN(
        account_id="111111111111",
        region="us-east-1",
        service="iam",
        resource_type="role",
        resource_id_parts=["test-role"],
    )


def test_get_resources(aws_interface_vpc):
    result = list(aws_interface_vpc.get_resources(service_name="ec2", resource_type="vpc", region="eu-west-1"))
    assert isinstance(result[0], CloudWandererResource)


def test_get_resource(aws_interface_role, cloudwanderer_dependent_urn, cloudwanderer_resource_urn):
    result = list(aws_interface_role.get_resource(urn=cloudwanderer_resource_urn))
    assert isinstance(result[0], CloudWandererResource)
    assert result[0].urn == cloudwanderer_dependent_urn
    assert result[0].parent_urn == cloudwanderer_resource_urn
    assert result[1].parent_urn is None
    assert result[1].urn == cloudwanderer_resource_urn
    assert result[1].dependent_resource_urns == [cloudwanderer_dependent_urn]
