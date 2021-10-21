from unittest.mock import ANY, MagicMock

from pytest import fixture

from cloudwanderer.aws_interface import CloudWandererAWSInterface
from cloudwanderer.models import ActionSet, ServiceResourceType, TemplateActionSet
from cloudwanderer.urn import PartialUrn


@fixture
def mock_action_set_vpc():
    return TemplateActionSet(
        get_urns=[
            PartialUrn(
                account_id="ALL",
                region="eu-west-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=["ALL"],
            ),
            PartialUrn(
                account_id="ALL",
                region="us-east-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=["ALL"],
            ),
        ],
        delete_urns=[
            PartialUrn(
                account_id="ALL",
                region="eu-west-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=["ALL"],
            ),
            PartialUrn(
                account_id="ALL",
                region="us-east-1",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=["ALL"],
            ),
        ],
    )


@fixture
def mock_action_set_s3():
    return TemplateActionSet(
        get_urns=[
            PartialUrn(
                account_id="ALL",
                region="us-east-1",
                service="s3",
                resource_type="bucket",
                resource_id_parts=["ALL"],
            )
        ],
        delete_urns=[
            PartialUrn(
                account_id="ALL",
                region="ALL",
                service="s3",
                resource_type="bucket",
                resource_id_parts=["ALL"],
            )
        ],
    )


@fixture
def mock_action_set_role():
    return TemplateActionSet(
        get_urns=[
            PartialUrn(
                account_id="ALL",
                region="us-east-1",
                service="iam",
                resource_type="role",
                resource_id_parts=["ALL"],
            )
        ],
        delete_urns=[
            PartialUrn(
                account_id="ALL",
                region="us-east-1",
                service="iam",
                resource_type="role",
                resource_id_parts=["ALL"],
            )
        ],
    )


@fixture
def mock_action_set_role_policy():
    return TemplateActionSet(
        get_urns=[],
        delete_urns=[
            PartialUrn(
                account_id="ALL",
                region="us-east-1",
                service="iam",
                resource_type="role_policy",
                resource_id_parts=["ALL"],
            )
        ],
    )


@fixture
def aws_interface() -> CloudWandererAWSInterface:
    mock_cloudwanderer_boto3_session = MagicMock(
        **{
            "get_available_resources.return_value": ["ec2"],
            "get_enabled_regions.return_value": ["us-east-1", "eu-west-1"],
            "resource.return_value": MagicMock(resource_types=["vpc"]),
            "get_account_id.return_value": "111111111111",
        }
    )
    return CloudWandererAWSInterface(cloudwanderer_boto3_session=mock_cloudwanderer_boto3_session)


def test_get_resource_discovery_actions(aws_interface: CloudWandererAWSInterface, mock_action_set_vpc):
    aws_interface._get_discovery_action_templates_for_service = MagicMock(return_value=[mock_action_set_vpc])

    result = aws_interface.get_resource_discovery_actions()

    assert len(result) == 1
    assert isinstance(result[0], ActionSet)
    assert result[0].delete_urns == [
        PartialUrn(
            account_id="111111111111", region=region, service="ec2", resource_type="vpc", resource_id_parts=["ALL"]
        )
        for region in ["eu-west-1", "us-east-1"]
    ]
    assert result[0].get_urns == [
        PartialUrn(
            account_id="111111111111", region=region, service="ec2", resource_type="vpc", resource_id_parts=["ALL"]
        )
        for region in ["eu-west-1", "us-east-1"]
    ]

    aws_interface._get_discovery_action_templates_for_service.assert_called_with(
        service=ANY, resource_types=[], discovery_regions=["us-east-1", "eu-west-1"]
    )


def test_get_resource_discovery_actions_specific_resource_type(
    aws_interface: CloudWandererAWSInterface, mock_action_set_vpc
):
    aws_interface._get_discovery_action_templates_for_service = MagicMock(return_value=[mock_action_set_vpc])

    result = aws_interface.get_resource_discovery_actions(
        service_resource_types=[ServiceResourceType(service_name="ec2", name="vpc")]
    )

    assert len(result) == 1
    assert isinstance(result[0], ActionSet)
    assert result[0].delete_urns == [
        PartialUrn(
            account_id="111111111111", region=region, service="ec2", resource_type="vpc", resource_id_parts=["ALL"]
        )
        for region in ["eu-west-1", "us-east-1"]
    ]
    assert result[0].get_urns == [
        PartialUrn(
            account_id="111111111111", region=region, service="ec2", resource_type="vpc", resource_id_parts=["ALL"]
        )
        for region in ["eu-west-1", "us-east-1"]
    ]

    aws_interface._get_discovery_action_templates_for_service.assert_called_with(
        service=ANY, resource_types=["vpc"], discovery_regions=["us-east-1", "eu-west-1"]
    )


def test_get_resource_discovery_actions_for_s3(aws_interface: CloudWandererAWSInterface, mock_action_set_s3):
    aws_interface._get_discovery_action_templates_for_service = MagicMock(return_value=[mock_action_set_s3])

    result = aws_interface.get_resource_discovery_actions()

    assert len(result) == 1
    assert isinstance(result[0], ActionSet)
    assert result[0].get_urns == [
        PartialUrn(
            account_id="111111111111", region=region, service="s3", resource_type="bucket", resource_id_parts=["ALL"]
        )
        for region in ["us-east-1"]
    ]
    assert result[0].delete_urns == [
        PartialUrn(
            account_id="111111111111", region=region, service="s3", resource_type="bucket", resource_id_parts=["ALL"]
        )
        for region in ["us-east-1", "eu-west-1"]
    ]
    aws_interface._get_discovery_action_templates_for_service.assert_called_with(
        service=ANY, resource_types=[], discovery_regions=["us-east-1", "eu-west-1"]
    )


def test_get__get_discovery_action_templates_for_service(aws_interface: CloudWandererAWSInterface):
    aws_interface._get_discovery_action_templates_for_resource = MagicMock()
    service = MagicMock(resource_types=["role"])

    aws_interface._get_discovery_action_templates_for_service(
        service=service, resource_types=[], discovery_regions=["eu-west-1"]
    )

    service.resource.assert_called_with("role", empty_resource=True)
    aws_interface._get_discovery_action_templates_for_resource.assert_called_with(
        service=ANY, resource=ANY, discovery_regions=["eu-west-1"]
    )


def test__get_discovery_action_templates_for_resource(
    aws_interface: CloudWandererAWSInterface, mock_action_set_role, mock_action_set_role_policy
):
    dependent_resource = MagicMock(**{"get_discovery_action_templates.return_value": [mock_action_set_role_policy]})
    service = MagicMock(
        **{
            "resource.return_value": dependent_resource,
        }
    )
    resource = MagicMock(
        **{
            "dependent_resource_types": ["role_policy"],
            "get_discovery_action_templates.return_value": [mock_action_set_role],
        }
    )

    result = aws_interface._get_discovery_action_templates_for_resource(
        service=service, resource=resource, discovery_regions=["eu-west-1"]
    )

    resource.get_discovery_action_templates.assert_called_with(discovery_regions=["eu-west-1"])
    dependent_resource.get_discovery_action_templates.assert_called_with(discovery_regions=["eu-west-1"])

    assert len(result) == 2
    assert isinstance(result[0], ActionSet)
    assert isinstance(result[1], ActionSet)
