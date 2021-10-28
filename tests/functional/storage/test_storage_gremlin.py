import logging
import platform
from datetime import datetime
from unittest.mock import ANY

import pytest
from gremlin_python.process.graph_traversal import __  # type: ignore
from gremlin_python.process.traversal import T, startingWith
from moto import mock_ec2, mock_iam, mock_sts

from cloudwanderer.storage_connectors import GremlinStorageConnector

from ...pytest_helpers import (
    compare_dict_allow_any,
    create_ec2_instances,
    get_inferred_ec2_instances,
    inferred_ec2_vpcs,
)
from .helpers import get_vertex_and_edges

logger = logging.getLogger(__name__)


@pytest.fixture
def gremlin_connector():
    connector = GremlinStorageConnector(endpoint_url="ws://localhost:8182", test_prefix=platform.python_version())
    yield connector
    # Clean up our tests' vertices and edges
    connector.g.V().has(T.id, startingWith(connector.test_prefix)).drop().toList()
    connector.g.E().has(T.id, startingWith(connector.test_prefix)).drop().toList()
    connector.close()


@mock_sts
@mock_iam
def test_write_resource_and_relationship(gremlin_connector, iam_role, iam_role_policies):
    gremlin_connector.write_resource(iam_role_policies[0])
    gremlin_connector.write_resource(resource=iam_role)
    result_1, result_2 = (
        gremlin_connector.g.V(gremlin_connector.generate_vertex_id(iam_role.urn))
        .both()
        .path()
        .by(__.valueMap(True))
        .toList()[0]
    )

    assert list(result_1.values()) == [
        ANY,
        "aws_iam_role",
        ["111111111111"],
        ["[{'PolicyNames': ['test-role']}]"],
        ["test-role"],
        ["test-role"],
        ["iam"],
        ["aws"],
        ["us-east-1"],
        [ANY],
        ["role"],
        ["urn:aws:111111111111:us-east-1:iam:role:test-role"],
    ]

    assert list(result_2.values()) == [
        ANY,
        "aws_iam_role_policy",
        ["111111111111"],
        ["test-role", "test-role-policy-1"],
        ["iam"],
        ["aws"],
        ["us-east-1"],
        [ANY],
        ["role_policy"],
        ["urn:aws:111111111111:us-east-1:iam:role_policy:test-role/test-role-policy-1"],
    ]


@mock_sts
@mock_ec2
def test_unknown_vertices_later_discovered_get_repointed(gremlin_connector, cloudwanderer_boto3_session):
    """If we discover a resource (A) which has a relationship with a resource (B) but resource B
    has not been discovered yet, ensure that resource B is created as UNKNOWN and then
    is overwritten and cleaned up once it is discovered.
    """
    create_ec2_instances()
    ec2_instance = get_inferred_ec2_instances(cloudwanderer_boto3_session)[0]
    vpc = inferred_ec2_vpcs(cloudwanderer_boto3_session)[0]

    # Step 1 write ec2 without vpc, vpc gets written as unknown
    gremlin_connector.write_resource(ec2_instance)

    result_1, result_2 = (
        gremlin_connector.g.V(gremlin_connector.generate_vertex_id(ec2_instance.urn))
        .both()
        .path()
        .by(__.valueMap(True))
        .toList()[0]
    )
    unknown_vpc_urn = result_2["_urn"][0]
    assert "urn:aws:111111111111:eu-west-2:ec2:instance:i-" in result_1["_urn"][0]
    assert "urn:aws:unknown:eu-west-2:ec2:vpc:vpc-" in unknown_vpc_urn

    # Step 2 write vpc, vpc unknown gets deleted and its edges repointed
    gremlin_connector.write_resource(vpc)

    result_1, result_2 = (
        gremlin_connector.g.V(gremlin_connector.generate_vertex_id(ec2_instance.urn))
        .both()
        .path()
        .by(__.valueMap(True))
        .toList()[0]
    )
    assert result_1["_urn"][0].startswith("urn:aws:111111111111:eu-west-2:ec2:instance:i-")
    assert result_2["_urn"][0].startswith("urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-")

    # Ensure the deleted vpc no longer exists
    unknown_vpc = gremlin_connector.g.V(unknown_vpc_urn).toList()

    assert unknown_vpc == []


@mock_sts
@mock_ec2
def test_write_then_read(gremlin_connector, cloudwanderer_boto3_session):
    vpc = inferred_ec2_vpcs(cloudwanderer_boto3_session)[0]

    gremlin_connector.write_resource(vpc)
    result = gremlin_connector.read_resource(urn=vpc.urn)

    compare_dict_allow_any(
        {
            "cidr_block": "172.31.0.0/16",
            "cidr_block_association_set": ANY,
            "cloudwanderer_metadata": {
                "CidrBlock": "172.31.0.0/16",
                "CidrBlockAssociationSet": ANY,
                "DhcpOptionsId": "dopt-7a8b9c2d",
                "InstanceTenancy": "default",
                "Ipv6CidrBlockAssociationSet": "[]",
                "IsDefault": "True",
                "State": "available",
                "Tags": "[]",
                "VpcId": ANY,
            },
            "dependent_resource_urns": [],
            "dhcp_options_id": ANY,
            "discovery_time": ANY,
            "instance_tenancy": "default",
            "ipv6_cidr_block_association_set": "[]",
            "is_default": "True",
            "parent_urn": None,
            "relationships": [],
            "state": "available",
            "tags": "[]",
            "urn": ANY,
            "vpc_id": ANY,
        },
        dict(result),
        allow_partial_match_first=True,
    )


@mock_sts
@mock_iam
def test_stale_edges_get_removed(gremlin_connector, iam_instance_profile):
    gremlin_connector.write_resource(resource=iam_instance_profile)
    result = get_vertex_and_edges(gremlin_connector, iam_instance_profile.urn)[0]

    assert result["v1"]["_urn"][0] == "urn:aws:111111111111:us-east-1:iam:instance_profile:my-test-profile"
    assert result["v2"]["_urn"][0] == "urn:aws:unknown:us-east-1:iam:role:test-role"

    # Remove the relationship with the role and ensure that we don't get a result
    # when we search for an edge on the instance profile
    iam_instance_profile.relationships = []
    iam_instance_profile.discovery_time = datetime.now()
    gremlin_connector.write_resource(resource=iam_instance_profile)

    assert (
        gremlin_connector.g.V(gremlin_connector.generate_vertex_id(iam_instance_profile.urn))
        .both()
        .path()
        .by(__.valueMap(True))
        .toList()
        == []
    )


@mock_sts
@mock_iam
def test_fresh_edges_do_not_get_removed(gremlin_connector, iam_instance_profile):
    gremlin_connector.write_resource(resource=iam_instance_profile)
    result = get_vertex_and_edges(gremlin_connector, iam_instance_profile.urn)[0]

    assert result["v1"]["_urn"][0] == "urn:aws:111111111111:us-east-1:iam:instance_profile:my-test-profile"
    assert result["v2"]["_urn"][0] == "urn:aws:unknown:us-east-1:iam:role:test-role"
    assert result["e"]["_discovery_time"] == iam_instance_profile.discovery_time.isoformat()

    # Write the same resource again with an updated timestamp and make sure the edge is still there.
    iam_instance_profile.discovery_time = datetime.now()

    gremlin_connector.write_resource(resource=iam_instance_profile)
    result = get_vertex_and_edges(gremlin_connector, iam_instance_profile.urn)[0]

    assert result["v1"]["_urn"][0] == "urn:aws:111111111111:us-east-1:iam:instance_profile:my-test-profile"
    assert result["v2"]["_urn"][0] == "urn:aws:unknown:us-east-1:iam:role:test-role"
    assert result["e"]["_discovery_time"] == iam_instance_profile.discovery_time.isoformat()
