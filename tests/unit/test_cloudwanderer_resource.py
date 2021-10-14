from pytest import fixture
from cloudwanderer import CloudWandererResource
from cloudwanderer.urn import URN


@fixture
def partial_urn():
    return URN(
        account_id="unknown",
        region="unknown",
        service="ec2",
        resource_type="vpc",
        resource_id_parts=["vpc-111111"],
    )


@fixture
def urn():
    return URN(
        account_id="111111111111",
        region="eu-west-1",
        service="ec2",
        resource_type="vpc",
        resource_id_parts=["vpc-111111"],
    )


def test_relationships(urn, partial_urn):
    subject = CloudWandererResource(urn=urn, resource_data={}, relationships=[partial_urn])

    assert subject.relationships == [partial_urn]
