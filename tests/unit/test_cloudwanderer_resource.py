import json
from datetime import datetime

import pytest

from cloudwanderer import CloudWandererResource
from cloudwanderer.urn import URN


@pytest.fixture
def partial_urn():
    return URN(
        account_id="unknown",
        region="unknown",
        service="ec2",
        resource_type="vpc",
        resource_id_parts=["vpc-111111"],
    )


@pytest.fixture
def urn():
    return URN(
        account_id="111111111111",
        region="eu-west-1",
        service="ec2",
        resource_type="vpc",
        resource_id_parts=["vpc-111111"],
    )


@pytest.fixture
def cloudwanderer_resource(urn, partial_urn):
    return CloudWandererResource(
        urn=urn,
        resource_data={"VpcId": "vpc-111111"},
        relationships=[partial_urn],
        discovery_time=datetime(2021, 10, 23),
    )


def test_relationships(cloudwanderer_resource, partial_urn):
    assert cloudwanderer_resource.relationships == [partial_urn]


def test_dict_conversion(cloudwanderer_resource):
    assert dict(cloudwanderer_resource) == {
        "urn": URN(
            cloud_name="aws",
            account_id="111111111111",
            region="eu-west-1",
            service="ec2",
            resource_type="vpc",
            resource_id_parts=["vpc-111111"],
        ),
        "relationships": [
            URN(
                cloud_name="aws",
                account_id="unknown",
                region="unknown",
                service="ec2",
                resource_type="vpc",
                resource_id_parts=["vpc-111111"],
            )
        ],
        "dependent_resource_urns": [],
        "parent_urn": None,
        "cloudwanderer_metadata": {"VpcId": "vpc-111111"},
        "discovery_time": datetime(2021, 10, 23, 0, 0),
        "vpc_id": "vpc-111111",
    }


def test_json_conversion(cloudwanderer_resource):

    assert json.dumps(dict(cloudwanderer_resource), default=str) == json.dumps(
        {
            "urn": "urn:aws:111111111111:eu-west-1:ec2:vpc:vpc-111111",
            "relationships": ["urn:aws:unknown:unknown:ec2:vpc:vpc-111111"],
            "dependent_resource_urns": [],
            "parent_urn": None,
            "cloudwanderer_metadata": {"VpcId": "vpc-111111"},
            "discovery_time": "2021-10-23 00:00:00",
            "vpc_id": "vpc-111111",
        }
    )
