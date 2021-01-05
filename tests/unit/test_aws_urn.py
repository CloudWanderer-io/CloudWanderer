import unittest
from cloudwanderer import AwsUrn


class TestAwsUrn(unittest.TestCase):

    def setUp(self):
        self.test_urn = AwsUrn(
            account_id='111111111111',
            region='us-east-1',
            service='ec2',
            resource_type='role_policy',
            resource_id='test-role:test-policy'
        )

    def test_from_string(self):
        assert AwsUrn.from_string(
            'urn:aws:111111111111:us-east-1:ec2:role_policy:test-role:test-policy') == self.test_urn

    def test_str(self):
        assert str(self.test_urn) == 'urn:aws:111111111111:us-east-1:ec2:role_policy:test-role:test-policy'

    def test_repr(self):
        assert repr(self.test_urn) == str(
            "AwsUrn("
            "account_id='111111111111', "
            "region='us-east-1', "
            "service='ec2', "
            "resource_type='role_policy', "
            "resource_id='test-role:test-policy')"
        )
