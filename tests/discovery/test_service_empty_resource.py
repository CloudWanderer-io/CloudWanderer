from boto3.resources.collection import ResourceCollection
from cloudwanderer.urn import PartialUrn, URN
from unittest.mock import MagicMock

from pytest import fixture

from cloudwanderer.aws_interface import CloudWandererBoto3Session


@fixture
def service_resource_ec2_vpc():
    session = CloudWandererBoto3Session()
    service = session.resource("ec2")
    return service.resource("vpc", empty_resource=True)


@fixture
def service_resource_s3_bucket():
    session = CloudWandererBoto3Session()
    service = session.resource("s3")
    return service.resource("bucket", empty_resource=True)


@fixture
def service_resource_iam_role():
    session = CloudWandererBoto3Session()
    service = session.resource("iam")
    return service.resource("role", empty_resource=True)


@fixture
def service_resource_iam_role_policy():
    session = CloudWandererBoto3Session()
    service = session.resource("iam")
    resource = service.resource("role", empty_resource=True)
    return resource.get_dependent_resource("role_policy", empty_resource=True)
    
@fixture
def service_resource_ec2_route():
    session = CloudWandererBoto3Session()
    service = session.resource("ec2")
    resource = service.resource("route_table", empty_resource=True)
    return resource.get_dependent_resource("route", empty_resource=True)


@fixture
def service_resource_iam():
    session = CloudWandererBoto3Session()
    return session.resource("iam")


def test_get_discovery_action_templates_regional_resource_regional_service(service_resource_ec2_vpc):
    action_template = service_resource_ec2_vpc.get_discovery_action_templates(discovery_regions=["eu-west-1"])

    assert action_template[0].get_urns == [
        PartialUrn(account_id=None, region="eu-west-1", service="ec2", resource_type="vpc", resource_id_parts=[None])
    ]
    assert action_template[0].delete_urns == [
        PartialUrn(account_id=None, region="eu-west-1", service="ec2", resource_type="vpc", resource_id_parts=[None])
    ]


def test_get_discovery_action_templates_regional_resource_global_service(service_resource_s3_bucket):
    action_template = service_resource_s3_bucket.get_discovery_action_templates(discovery_regions=["us-east-1"])

    assert action_template[0].get_urns == [
        PartialUrn(account_id=None, region="us-east-1", service="s3", resource_type="bucket", resource_id_parts=[None])
    ]
    assert action_template[0].delete_urns == [
        PartialUrn(
            account_id=None, region="ALL_REGIONS", service="s3", resource_type="bucket", resource_id_parts=[None]
        )
    ]


def test_dependent_resources_subresource(service_resource_iam_role_policy):
    action_template = service_resource_iam_role_policy.get_discovery_action_templates(discovery_regions=["us-east-1"])

    assert action_template[0].get_urns == []
    assert action_template[0].delete_urns == [
        PartialUrn(
            account_id=None, region="us-east-1", service="iam", resource_type="role_policy", resource_id_parts=[None]
        )
    ]

def test_dependent_resources_reference(service_resource_ec2_route):
    action_template = service_resource_ec2_route.get_discovery_action_templates(discovery_regions=["us-east-1"])

    assert action_template[0].get_urns == []
    assert action_template[0].delete_urns == [
        PartialUrn(
            account_id=None, region="us-east-1", service="ec2", resource_type="route", resource_id_parts=[]
        )
    ]


def test_collection(service_resource_iam):
    collection = service_resource_iam.collection(resource_type="role")
    assert issubclass(collection.__class__, ResourceCollection)


def test_dependent_resource_types(service_resource_iam_role):
    result = service_resource_iam_role.dependent_resource_types
    assert result == ["role_policy"]
