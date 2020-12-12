import unittest
from cloudwanderer import AwsUrn


class TestAwsUrn(unittest.TestCase):

    def setUp(self):
        self.test_urn = AwsUrn(
            account_id='111111111111',
            region='eu-west-2',
            service='ec2',
            resource_type='vpc',
            resource_id='vpc-11111111'
        )

    def test_from_string(self):
        assert AwsUrn.from_string('urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111') == self.test_urn

    def test_str(self):
        assert str(self.test_urn) == 'urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111'

    def test_repr(self):
        assert repr(self.test_urn) == str(
            "AwsUrn("
            "account_id='111111111111', "
            "region='eu-west-2', "
            "service='ec2', "
            "resource_type='vpc', "
            "resource_id='vpc-11111111')"
        )
