import unittest
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
        assert cwr.enable_dns_support == {'Value': True}

    def test_clashing_attributes(self):
        urn = AwsUrn.from_string('urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111')
        with self.assertLogs('cloudwanderer.cloud_wanderer_resource', level='WARNING') as cm:
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
        self.assertEqual(cm.output, [str(
            'WARNING:cloudwanderer.cloud_wanderer_resource:EnableDnsSupport is already an '
            'attribute on CloudWandererResource, EnableDnsSupport will only be accessible '
            'via get_secondary_attributes')])
        assert cwr.enable_dns_support == {'Value': True}
        assert cwr.get_secondary_attribute('[].EnableDnsSupport.Value') == [True, False]
