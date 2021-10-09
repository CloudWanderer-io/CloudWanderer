from boto3.resources.collection import ResourceCollection
import botocore
from cloudwanderer.urn import PartialUrn, URN
from unittest.mock import MagicMock

from pytest import fixture

from cloudwanderer.aws_interface import CloudWandererBoto3Session


@fixture
def botocore_session():
    botocore_session = botocore.session.Session()
    botocore_session.create_client = MagicMock(
        **{
            "return_value.get_bucket_location.return_value": {"LocationConstraint": "eu-west-1"},
            "return_value.describe_vpc_attribute.return_value": {
                "VpcId": "vpc-11111",
                "EnableDnsSupport": {"Value": True},
            },
        }
    )
    return botocore_session


@fixture
def cloudwanderer_boto3_session(botocore_session):
    session = CloudWandererBoto3Session(botocore_session=botocore_session)
    session.get_account_id = MagicMock(return_value="111111111111")
    return session


@fixture
def service_resource_ec2_vpc(cloudwanderer_boto3_session):
    service = cloudwanderer_boto3_session.resource("ec2")
    return service.resource(resource_type="vpc", identifiers=["vpc-11111"])


@fixture
def service_resource_s3_bucket(cloudwanderer_boto3_session):
    service = cloudwanderer_boto3_session.resource("s3")
    return service.resource(resource_type="bucket", identifiers=["my_bucket"])


def test_get_urn(service_resource_s3_bucket):
    urn = service_resource_s3_bucket.get_urn()
    assert urn == URN(
        account_id="111111111111",
        region="eu-west-1",
        service="s3",
        resource_type="bucket",
        resource_id_parts=["my_bucket"],
    )


def test_get_account_id(service_resource_s3_bucket):
    account_id = service_resource_s3_bucket.get_account_id()
    assert account_id == "111111111111"


def test_get_region(service_resource_s3_bucket):
    region = service_resource_s3_bucket.get_region()
    assert region == "eu-west-1"


def test_get_secondary_attributes(service_resource_ec2_vpc):
    assert list(service_resource_ec2_vpc.get_secondary_attributes()) == [
        {"EnableDnsSupport": {"Value": True}, "VpcId": "vpc-11111"}
    ]


def test_normalized_raw_data(service_resource_ec2_vpc):
    service_resource_ec2_vpc.meta.data = {"CidrBlock": "10.16.0.0/16", "VpcId": "vpc-11111"}
    service_resource_ec2_vpc.meta.client.meta.service_model.shape_for.return_value.members = {
        "CidrBlock": {},
        "DhcpOptionsId": {},
        "State": {},
        "VpcId": {},
        "OwnerId": {},
        "InstanceTenancy": {},
        "Ipv6CidrBlockAssociationSet": {},
        "CidrBlockAssociationSet": {},
        "IsDefault": {},
        "Tags": {},
    }
    assert service_resource_ec2_vpc.normalized_raw_data == {
        "CidrBlock": "10.16.0.0/16",
        "CidrBlockAssociationSet": None,
        "DhcpOptionsId": None,
        "InstanceTenancy": None,
        "Ipv6CidrBlockAssociationSet": None,
        "IsDefault": None,
        "OwnerId": None,
        "State": None,
        "Tags": None,
        "VpcId": "vpc-11111",
    }
