from cloudwanderer.urn import PartialUrn
from cloudwanderer.models import ActionSet
from pytest import fixture
from unittest.mock import ANY, MagicMock
from cloudwanderer.aws_interface import CloudWandererAWSInterface


@fixture
def mock_action_set():
    return ActionSet(
        get_urns=[
            PartialUrn(
                account_id="111111111111",
                region="eu-west-1",
                service="ec2",
                resource_type="vpc",
                resource_id="ALL",
            )
        ],
        delete_urns=[
            PartialUrn(
                account_id="111111111111",
                region="eu-west-1",
                service="ec2",
                resource_type="vpc",
                resource_id="ALL",
            )
        ],
    )


@fixture
def aws_interface() -> CloudWandererAWSInterface:
    mock_cloudwanderer_boto3_session = MagicMock(
        **{
            "available_services": ["ec2"],
            "enabled_regions": ["eu-west-1"],
            "resource.return_value": MagicMock(resource_types=["vpc"]),
        }
    )
    return CloudWandererAWSInterface(cloudwanderer_boto3_session=mock_cloudwanderer_boto3_session)


def test_get_resource_discovery_actions(aws_interface: CloudWandererAWSInterface):
    aws_interface._get_discovery_actions_for_service = MagicMock()

    aws_interface.get_resource_discovery_actions()

    aws_interface._get_discovery_actions_for_service.assert_called_with(
        service=ANY, resource_types=[], discovery_regions=["eu-west-1"]
    )


def test_get__get_discovery_actions_for_service(aws_interface: CloudWandererAWSInterface):
    aws_interface._get_discovery_actions_for_resource = MagicMock()
    service = MagicMock(resource_types=["role"])

    aws_interface._get_discovery_actions_for_service(
        service=service, resource_types=[], discovery_regions=["eu-west-1"]
    )

    service.resource.assert_called_with("role")
    aws_interface._get_discovery_actions_for_resource.assert_called_with(resource=ANY, discovery_regions=["eu-west-1"])


def test__get_discovery_actions_for_resource(aws_interface: CloudWandererAWSInterface, mock_action_set):
    resource = MagicMock(
        **{
            "dependent_resource_types": ["role_policy"],
            "get_discovery_action_templates.return_value": [mock_action_set],
        }
    )

    aws_interface._get_discovery_actions_for_resource(resource=resource, discovery_regions=["eu-west-1"])

    resource.get_discovery_action_templates.assert_called_with(discovery_regions=["eu-west-1"])
