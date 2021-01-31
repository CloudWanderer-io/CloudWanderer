import boto3
import unittest
from unittest.mock import ANY
from cloudwanderer import CloudWandererBoto3Interface
from ..helpers import get_default_mocker


class TestBoto3Interface(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        get_default_mocker().start_general_mock()
        cls.ec2 = boto3.resource('ec2')
        cls.vpcs = list(cls.ec2.vpcs.all())
        cls.boto3_interface = CloudWandererBoto3Interface()

    @classmethod
    def tearDownClass(cls):
        get_default_mocker().stop_general_mock()

    def test__get_resource_attributes(self):
        assert list(self.boto3_interface._get_resource_attributes(self.vpcs[0])) == [
            'CidrBlock',
            'DhcpOptionsId',
            'State',
            'VpcId',
            'OwnerId',
            'InstanceTenancy',
            'Ipv6CidrBlockAssociationSet',
            'CidrBlockAssociationSet',
            'IsDefault',
            'Tags',
        ]

    def test__prepare_boto3_resource_data(self):
        assert self.boto3_interface._prepare_boto3_resource_data(self.vpcs[0]) == {
            'CidrBlock': '172.31.0.0/16',
            'CidrBlockAssociationSet': [{
                'AssociationId': ANY,
                'CidrBlock': '172.31.0.0/16',
                'CidrBlockState': {'State': 'associated'}
            }],
            'DhcpOptionsId': 'dopt-7a8b9c2d',
            'InstanceTenancy': 'default',
            'Ipv6CidrBlockAssociationSet': [],
            'IsDefault': True,
            'OwnerId': None,
            'State': 'available',
            'Tags': [],
            'VpcId': ANY,
        }
