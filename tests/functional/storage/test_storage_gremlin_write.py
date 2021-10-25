from unittest.mock import ANY

import pytest
from gremlin_python.process.graph_traversal import __  # type: ignore
from moto import mock_iam, mock_sts

from cloudwanderer.storage_connectors import GremlinStorageConnector


@pytest.fixture
def gremlin_connector():
    connector = GremlinStorageConnector(endpoint_url="ws://localhost:8182")
    yield connector
    connector.close()


@mock_sts
@mock_iam
def test_write_resource_and_relationship(gremlin_connector, iam_role, iam_role_policies):
    gremlin_connector.write_resource(iam_role_policies[0])
    gremlin_connector.write_resource(resource=iam_role)
    result_1, result_2 = gremlin_connector.g.V(str(iam_role.urn)).both().path().by(__.valueMap(True)).toList()[0]

    assert list(result_1.values()) == [
        "urn:aws:111111111111:us-east-1:iam:role:test-role",
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
        "urn:aws:111111111111:us-east-1:iam:role_policy:test-role/test-role-policy-1",
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
