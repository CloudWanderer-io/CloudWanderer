import unittest
from unittest.mock import MagicMock
from cloudwanderer import AwsUrn
from cloudwanderer.cloud_wanderer_resource import CloudWandererResource


class TestCloudWandererResource(unittest.TestCase):

    def test_default(self):
        urn = AwsUrn.from_string('urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111')
        cwr = CloudWandererResource(
            urn=urn,
            resource_data={
                'CidrBlock': '10.0.0.0/0'
            },
            secondary_attributes=[{'EnableDnsSupport': {'Value': True}}]
        )

        assert cwr.urn == urn
        assert cwr.cidr_block == '10.0.0.0/0'
        assert cwr.get_secondary_attribute('[].EnableDnsSupport.Value')[0] is True
        self.assertRaises(AttributeError, getattr, cwr, 'enable_dns_support')
        assert cwr.is_inflated is True

    def test_clashing_attributes(self):
        urn = AwsUrn.from_string('urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111')
        cwr = CloudWandererResource(
            urn=urn,
            resource_data={
                'CidrBlock': '10.0.0.0/0'
            },
            secondary_attributes=[
                {'EnableDnsSupport': {'Value': True}},
                {'EnableDnsSupport': {'Value': False}}
            ]
        )
        assert cwr.get_secondary_attribute('[].EnableDnsSupport.Value') == [True, False]
        self.assertRaises(AttributeError, getattr, cwr, 'enable_dns_support')
        assert cwr.is_inflated is True

    def test_load_without_loader(self):
        urn = AwsUrn.from_string('urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111')
        cwr = CloudWandererResource(
            urn=urn,
            resource_data={},
            secondary_attributes=[{'EnableDnsSupport': {'Value': True}}]
        )
        assert cwr.is_inflated is False
        self.assertRaises(ValueError, cwr.load)

    def test_load_with_loader(self):
        urn = AwsUrn.from_string('urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111')
        mock_loader = MagicMock(return_value=CloudWandererResource(
            urn=urn,
            resource_data={
                'CidrBlock': '10.0.0.0/0'
            },
            secondary_attributes=[{'EnableDnsSupport': {'Value': True}}]
        ))
        cwr = CloudWandererResource(
            urn=urn,
            resource_data={},
            secondary_attributes=[],
            loader=mock_loader
        )
        assert cwr.is_inflated is False
        cwr.load()
        assert cwr.is_inflated is True
        assert cwr.cidr_block == '10.0.0.0/0'

    def test_str(self):
        cwr = CloudWandererResource(
            urn=AwsUrn.from_string('urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111'),
            resource_data={
                'CidrBlock': '10.0.0.0/0'
            },
            secondary_attributes=[{'EnableDnsSupport': {'Value': True}}]
        )

        assert str(cwr) == str(
            "CloudWandererResource("
            "urn=AwsUrn(account_id='111111111111', region='eu-west-2', service='ec2', "
            "resource_type='vpc', resource_id='vpc-11111111'), "
            "resource_data={'CidrBlock': '10.0.0.0/0'}, secondary_attributes=[{'EnableDnsSupport': {'Value': True}}]"
            ")"
        )

    def test_repr(self):
        cwr = CloudWandererResource(
            urn=AwsUrn.from_string('urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111'),
            resource_data={
                'CidrBlock': '10.0.0.0/0'
            },
            secondary_attributes=[{'EnableDnsSupport': {'Value': True}}]
        )

        assert repr(cwr) == str(
            "CloudWandererResource("
            "urn=AwsUrn(account_id='111111111111', region='eu-west-2', service='ec2', "
            "resource_type='vpc', resource_id='vpc-11111111'), "
            "resource_data={'CidrBlock': '10.0.0.0/0'}, secondary_attributes=[{'EnableDnsSupport': {'Value': True}}]"
            ")"
        )
