from unittest.mock import MagicMock

from pytest import fixture

from cloudwanderer.aws_interface import CloudWandererBoto3Session


@fixture
def service_resource():
    session = CloudWandererBoto3Session()
    return session.resource("ec2")


def test_get_resource_discovery_actions_specify_resource_type(service_resource):
    action_sets = service_resource.get_resource_discovery_actions(resource_types=["vpc"], regions=["eu-west-1"])

    assert len(action_sets) == 1


def test_get_resource_discovery_actions(service_resource):
    action_sets = service_resource.get_resource_discovery_actions(resource_types=[], regions=["eu-west-1"])

    assert len(action_sets) >= 17
