import unittest

from cloudwanderer import URN


class TestURN(unittest.TestCase):
    def setUp(self):
        self.test_urn_subresource = URN(
            account_id="111111111111",
            region="us-east-1",
            service="iam",
            resource_type="role_policy",
            resource_id="test-role/test-policy",
        )
        self.test_urn_resource = URN(
            account_id="111111111111",
            region="us-east-1",
            service="iam",
            resource_type="role",
            resource_id="test-role",
        )

    def test_from_string(self):
        assert (
            URN.from_string("urn:aws:111111111111:us-east-1:iam:role_policy:test-role/test-policy")
            == self.test_urn_subresource
        )

    def test_from_string_with_nonstandard_extra_parts(self):
        assert (
            URN.from_string(
                "urn:aws:111111111111:us-east-1:iam:" "role_policy:test-role/test-policy:this:should:not:be:included"
            )
            == self.test_urn_subresource
        )

    def test_str(self):
        assert str(self.test_urn_subresource) == "urn:aws:111111111111:us-east-1:iam:role_policy:test-role/test-policy"

    def test_repr(self):
        assert repr(self.test_urn_subresource) == str(
            "URN("
            "account_id='111111111111', "
            "region='us-east-1', "
            "service='iam', "
            "resource_type='role_policy', "
            "resource_id='test-role/test-policy')"
        )

    def test_is_subresource(self):
        assert self.test_urn_subresource.is_subresource
        assert not self.test_urn_resource.is_subresource

    def test_equality(self):
        assert URN(
            account_id="123456789012",
            region="us-east-1",
            service="iam",
            resource_type="role_policy",
            resource_id="test-role/test-role-policy",
        ) == URN(
            account_id="123456789012",
            region="us-east-1",
            service="iam",
            resource_type="role_policy",
            resource_id="test-role/test-role-policy",
        )

    def test_parent_resource_id(self):

        assert self.test_urn_subresource.parent_resource_id == "test-role"
