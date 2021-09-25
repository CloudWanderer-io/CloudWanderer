from cloudwanderer.urn import PartialUrn
from cloudwanderer.models import ActionSet
from cloudwanderer.aws_interface import CloudWandererBoto3Session
from pytest import fixture
from unittest.mock import MagicMock


@fixture
def cloudwanderer_boto3_session():
    cloudwanderer_boto3_session = CloudWandererBoto3Session()
    cloudwanderer_boto3_session.resource = MagicMock(
        **{
            "return_value.get_resource_discovery_actions.return_value": [
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
            ]
        }
    )
    return cloudwanderer_boto3_session


def test_get_resource_discovery_actions(cloudwanderer_boto3_session: CloudWandererBoto3Session):
    actions = cloudwanderer_boto3_session.get_resource_discovery_actions(
        services_resource_tuples=[("ec2", "vpc")], regions=["eu-west-1"]
    )

    cloudwanderer_boto3_session.resource.assert_called_with(service_name="ec2")
    cloudwanderer_boto3_session.resource.return_value.get_resource_discovery_actions.assert_called_with(
        resource_types=["vpc"], regions=["eu-west-1"]
    )
    assert len(actions) == 1
    assert isinstance(actions[0], ActionSet)
