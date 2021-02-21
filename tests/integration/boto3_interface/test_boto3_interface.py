import unittest
from unittest.mock import ANY

import boto3

from cloudwanderer import CloudWandererAWSInterface
from cloudwanderer.boto3_helpers import _get_resource_attributes, _prepare_boto3_resource_data

from ..helpers import get_default_mocker


class TestBoto3Interface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        get_default_mocker().start_general_mock()
        cls.ec2 = boto3.resource("ec2")
        cls.vpcs = list(cls.ec2.vpcs.all())
        cls.aws_interface = CloudWandererAWSInterface()

    @classmethod
    def tearDownClass(cls):
        get_default_mocker().stop_general_mock()

    def test__get_resource_attributes(self):
        assert list(_get_resource_attributes(self.vpcs[0])) == [
            "CidrBlock",
            "DhcpOptionsId",
            "State",
            "VpcId",
            "OwnerId",
            "InstanceTenancy",
            "Ipv6CidrBlockAssociationSet",
            "CidrBlockAssociationSet",
            "IsDefault",
            "Tags",
        ]

    def test__prepare_boto3_resource_data(self):
        assert _prepare_boto3_resource_data(self.vpcs[0]) == {
            "CidrBlock": "172.31.0.0/16",
            "CidrBlockAssociationSet": [
                {"AssociationId": ANY, "CidrBlock": "172.31.0.0/16", "CidrBlockState": {"State": "associated"}}
            ],
            "DhcpOptionsId": "dopt-7a8b9c2d",
            "InstanceTenancy": "default",
            "Ipv6CidrBlockAssociationSet": [],
            "IsDefault": True,
            "OwnerId": None,
            "State": "available",
            "Tags": [],
            "VpcId": ANY,
        }
