from boto3.resources.base import ServiceResource
from moto import mock_ec2


def test_resource_types(ec2_service):
    assert {"instance", "internet_gateway", "vpc"}.issubset(set(ec2_service.resource_types))


@mock_ec2
def test_collection_all(ec2_service):
    assert isinstance(list(ec2_service.collection("vpc").all())[0], ServiceResource)


def test_empty_resource(ec2_service):
    vpc = ec2_service.resource("vpc", empty_resource=True)

    assert isinstance(vpc, ServiceResource)


# @mock_ec2
# TODO: resupport resource filtering
# def test_get_resources_filtered(ec2_service):
#     results = self.service.get_resources("vpc", resource_filters={"MaxResults": 5})
#     assert isinstance(next(results), CloudWandererBoto3Resource)
