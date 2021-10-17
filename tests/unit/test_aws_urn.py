import unittest

from cloudwanderer import URN


class TestURN(unittest.TestCase):
    def setUp(self):
        self.test_urn_dependent_resource = URN(
            account_id="111111111111",
            region="us-east-1",
            service="iam",
            resource_type="role_policy",
            resource_id_parts=["test-role", "test-policy"],
        )
        self.test_urn_resource = URN(
            account_id="111111111111",
            region="us-east-1",
            service="iam",
            resource_type="role",
            resource_id_parts=["test-role"],
        )

    def test_from_string(self):
        assert (
            URN.from_string("urn:aws:111111111111:us-east-1:iam:role_policy:test-role/test-policy")
            == self.test_urn_dependent_resource
        )

    def test_from_string_with_multiple_ids(self):
        assert URN.from_string(
            "urn:aws:111111111111:us-east-1:iam:role_policy:test-role/test-policy/this/should/be/included"
        ) == URN(
            account_id="111111111111",
            region="us-east-1",
            service="iam",
            resource_type="role_policy",
            resource_id_parts=["test-role", "test-policy", "this", "should", "be", "included"],
        )

    def test_str(self):
        assert (
            str(self.test_urn_dependent_resource)
            == "urn:aws:111111111111:us-east-1:iam:role_policy:test-role/test-policy"
        )

    def test_repr(self):
        assert repr(self.test_urn_dependent_resource) == str(
            "URN("
            "cloud_name='aws', "
            "account_id='111111111111', "
            "region='us-east-1', "
            "service='iam', "
            "resource_type='role_policy', "
            "resource_id_parts=['test-role', 'test-policy'])"
        )

    def test_equality(self):
        assert URN(
            account_id="123456789012",
            region="us-east-1",
            service="iam",
            resource_type="role_policy",
            resource_id_parts=["test-role", "test-role-policy"],
        ) == URN(
            account_id="123456789012",
            region="us-east-1",
            service="iam",
            resource_type="role_policy",
            resource_id_parts=["test-role", "test-role-policy"],
        )

    def test_resource_id_with_slashes(self):
        urn = URN(
            account_id="080863329876",
            region="eu-west-1",
            service="cloudwatch",
            resource_type="metric",
            resource_id_parts=["AWS/Logs/IncomingBytes"],
        )

        assert str(urn) == r"urn:aws:080863329876:eu-west-1:cloudwatch:metric:AWS\/Logs\/IncomingBytes"
        assert urn.resource_id == r"AWS\/Logs\/IncomingBytes"

    def test_resource_id_parts_with_slashes(self):
        urn = URN(
            account_id="080863329876",
            region="eu-west-1",
            service="cloudwatch",
            resource_type="metric",
            resource_id_parts=["AWS/Logs", "IncomingBytes"],
        )

        assert str(urn) == r"urn:aws:080863329876:eu-west-1:cloudwatch:metric:AWS\/Logs/IncomingBytes"
        assert urn.resource_id_parts == [r"AWS/Logs", r"IncomingBytes"]
        assert urn.resource_id == r"AWS\/Logs/IncomingBytes"

    def test_resource_id_with_slashes_from_string(self):
        urn = URN.from_string(r"urn:aws:080863329876:eu-west-1:cloudwatch:metric:AWS\/Logs\/IncomingBytes")

        assert urn == URN(
            account_id="080863329876",
            region="eu-west-1",
            service="cloudwatch",
            resource_type="metric",
            resource_id_parts=["AWS/Logs/IncomingBytes"],
        )
        assert urn.resource_id_parts == ["AWS/Logs/IncomingBytes"]

    def test_from_string_errors_with_no_id(self):
        with self.assertRaisesRegex(
            ValueError, "Resource ID must be supplied as the 7th element in a colon separated string"
        ):
            URN.from_string(r"urn:aws:080863329876:eu-west-1:cloudwatch:metric")

    def test_resource_id_with_integer(self):
        urn = URN.from_string(r"urn:aws:080863329876:eu-west-1:lambda:layer_version:test_layer/1")

        assert urn == URN(
            account_id="080863329876",
            region="eu-west-1",
            service="lambda",
            resource_type="layer_version",
            resource_id_parts=["test_layer", "1"],
        )
        assert urn.resource_id_parts == ["test_layer", "1"]

    def test_is_dependent_resource_false(self):
        assert not self.test_urn_resource.is_dependent_resource

    def test_is_dependent_resource_true(self):
        assert self.test_urn_dependent_resource.is_dependent_resource

    def test_cloud_service_resource_label(self):
        assert self.test_urn_resource.cloud_service_resource_label == "aws_iam_role"
