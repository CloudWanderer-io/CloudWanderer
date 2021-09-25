from cloudwanderer.urn import PartialUrn
from cloudwanderer.models import ActionSet
from pytest import fixture
from unittest.mock import MagicMock
from cloudwanderer.aws_interface import CloudWandererAWSInterface


@fixture
def aws_interface():
    mock_cloudwanderer_boto3_session = MagicMock(
        **{
            "enabled_regions": ["eu-west-1"],
            "get_resource_discovery_actions.return_value": [
                ActionSet(
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
            ],
        }
    )
    return CloudWandererAWSInterface(cloudwanderer_boto3_session=mock_cloudwanderer_boto3_session)


def test_get_actions(aws_interface):
    actions = aws_interface.get_resource_discovery_actions()

    aws_interface.cloudwanderer_boto3_session.get_resource_discovery_actions.assert_called_with(
        services_resource_tuples=[], regions=["eu-west-1"]
    )
    assert len(actions) == 1
    assert isinstance(actions[0], ActionSet)
