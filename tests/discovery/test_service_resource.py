from unittest.mock import MagicMock

import botocore
from pytest import fixture

from cloudwanderer.aws_interface import CloudWandererBoto3Session
from cloudwanderer.models import Relationship, RelationshipDirection
from cloudwanderer.urn import URN, PartialUrn


@fixture
def botocore_session():
    botocore_session = botocore.session.Session()
    botocore_session.create_client = MagicMock(
        **{
            "return_value.get_bucket_location.return_value": {"LocationConstraint": "eu-west-1"},
            "return_value.describe_vpcs.return_value": {
                "Vpcs": [
                    {
                        "VpcId": "vpc-11111",
                        "DhcpOptionsId": "dopt-mock",
                    }
                ]
            },
            "return_value.describe_vpc_attribute.return_value": {
                "VpcId": "vpc-11111",
                "EnableDnsSupport": {"Value": True},
            },
            "return_value.get_function.return_value": {
                "Configuration": {"Layers": [{"Arn": "arn:aws:lambda:eu-west-1:111111111111:layer:test-layer:2"}]}
            },
            "return_value.meta.region_name": "eu-west-1",
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
    resource = service.resource(resource_type="vpc", identifiers=["vpc-11111"])
    resource.load()
    resource.fetch_secondary_attributes()
    return resource


@fixture
def service_resource_lambda_function(cloudwanderer_boto3_session):
    service = cloudwanderer_boto3_session.resource("lambda")
    resource = service.resource(resource_type="function", identifiers=["test-function"])
    resource.load()
    resource.fetch_secondary_attributes()
    return resource


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


def test_secondary_attributes_map(service_resource_ec2_vpc):
    assert service_resource_ec2_vpc.secondary_attributes_map == {"EnableDnsSupport": True}


def test_secondary_attribute_names(service_resource_ec2_vpc):
    assert list(service_resource_ec2_vpc.secondary_attribute_names) == ["vpc_enable_dns_support"]


def test_shape(service_resource_ec2_vpc):
    service_resource_ec2_vpc.meta.client.meta.service_model.shape_for.assert_any_call("Vpc")


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
        "EnableDnsSupport": True,
        "InstanceTenancy": None,
        "Ipv6CidrBlockAssociationSet": None,
        "IsDefault": None,
        "OwnerId": None,
        "State": None,
        "Tags": None,
        "VpcId": "vpc-11111",
    }


def test_relationships(service_resource_ec2_vpc):
    assert service_resource_ec2_vpc.relationships == [
        Relationship(
            partial_urn=PartialUrn(
                cloud_name="aws",
                account_id="unknown",
                region="eu-west-1",
                service="ec2",
                resource_type="dhcp_options",
                resource_id_parts=["dopt-mock"],
            ),
            direction=RelationshipDirection.OUTBOUND,
        )
    ]


def test_relationships_arn(service_resource_lambda_function):
    assert service_resource_lambda_function.relationships == [
        Relationship(
            partial_urn=PartialUrn(
                cloud_name="aws",
                account_id="111111111111",
                region="eu-west-1",
                service="lambda",
                resource_type="layer_version",
                resource_id_parts=["test-layer", "2"],
            ),
            direction=RelationshipDirection.OUTBOUND,
        )
    ]
