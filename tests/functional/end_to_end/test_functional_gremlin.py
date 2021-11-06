import logging

import pytest

from cloudwanderer import CloudWanderer
from cloudwanderer.aws_interface.interface import CloudWandererAWSInterface
from cloudwanderer.models import ServiceResourceType
from cloudwanderer.storage_connectors import GremlinStorageConnector

ENDPOINT_URL = "ws://localhost:8182"


@pytest.fixture
def storage_connector():
    connector = GremlinStorageConnector(
        endpoint_url=ENDPOINT_URL,
    )
    yield connector
    connector.close()


@pytest.fixture
def cloudwanderer(storage_connector):
    storage_connector.init()
    return CloudWanderer(storage_connectors=[storage_connector])


# The _a_ in this test name ensures this test runs first so that subsequent read tests have values to read.
def test_a_write_resources_concurrently(cloudwanderer):
    """It is sufficient for this not to throw an exception."""
    logging.basicConfig(level="debug")
    cloudwanderer.write_resources_concurrently(
        cloud_interface_generator=lambda: CloudWandererAWSInterface(),
        storage_connector_generator=lambda: [
            GremlinStorageConnector(
                endpoint_url=ENDPOINT_URL,
            )
        ],
    )


def test_write_resources_in_region(cloudwanderer):
    """It is sufficient for this not to throw an exception."""
    cloudwanderer.write_resources(regions=["us-east-1"], exclude_resources=[])


def test_write_resource_type(cloudwanderer):
    """It is sufficient for this not to throw an exception."""
    cloudwanderer.write_resources(regions=["us-east-1"], service_resource_types=[ServiceResourceType("iam", "policy")])


def test_read_all(storage_connector):
    result = next(storage_connector.read_all(), None)
    assert result
    assert isinstance(result, dict)


def test_read_resource_of_type(storage_connector):
    vpcs = [
        resource
        for resource in storage_connector.read_resources(cloud_name="aws", service="ec2", resource_type="vpc")
        if not resource.urn.is_partial
    ]
    assert len(vpcs) > 0
    assert all(isinstance(x, str) for x in vpcs[0].cloudwanderer_metadata.resource_data.values())
    logging.info(vpcs[0])
    assert vpcs[0].is_default in ["True", "False"]
