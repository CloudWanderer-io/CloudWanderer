import unittest
from cloud_wanderer import AwsUrn


class TestAwsUrn(unittest.TestCase):

    def test_from_string(self):
        assert AwsUrn.from_string('urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111') == AwsUrn(
            account_id='111111111111',
            region='eu-west-2',
            service='ec2',
            resource_type='vpc',
            resource_id='vpc-11111111'
        )
