import unittest
from unittest.mock import MagicMock

from cloudwanderer import URN
from cloudwanderer.cloud_wanderer_resource import CloudWandererResource, SecondaryAttribute


class TestCloudWandererResource(unittest.TestCase):
    def test_default(self):
        urn = URN.from_string("urn:aws:111111111111:us-east-1:iam:role:test-role")
        cwr = CloudWandererResource(
            urn=urn,
            resource_data={"RoleName": "test-role"},
            subresource_urns=[URN.from_string("urn:aws:111111111111:us-east-1:iam:role_policy:test-role/test-policy")],
            secondary_attributes=[
                SecondaryAttribute(name="role_inline_policy_attachments", **{"PolicyNames": ["test-policy"]})
            ],
        )

        assert cwr.urn == urn
        assert cwr.role_name == "test-role"
        assert cwr.get_secondary_attribute(jmes_path="[].PolicyNames")[0] == ["test-policy"]
        assert cwr.get_secondary_attribute(name="role_inline_policy_attachments") == [{"PolicyNames": ["test-policy"]}]
        assert cwr.is_inflated is True

    def test_clashing_attributes(self):
        urn = URN.from_string("urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111")
        cwr = CloudWandererResource(
            urn=urn,
            resource_data={"CidrBlock": "10.0.0.0/0"},
            secondary_attributes=[{"EnableDnsSupport": {"Value": True}}, {"EnableDnsSupport": {"Value": False}}],
        )
        assert cwr.get_secondary_attribute(jmes_path="[].EnableDnsSupport.Value") == [True, False]
        self.assertRaises(AttributeError, getattr, cwr, "enable_dns_support")
        assert cwr.is_inflated is True

    def test_load_without_loader(self):
        urn = URN.from_string("urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111")
        cwr = CloudWandererResource(
            urn=urn, resource_data={}, secondary_attributes=[{"EnableDnsSupport": {"Value": True}}]
        )
        assert cwr.is_inflated is False
        self.assertRaises(ValueError, cwr.load)

    def test_load_with_loader(self):
        urn = URN.from_string("urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111")
        mock_loader = MagicMock(
            return_value=CloudWandererResource(
                urn=urn,
                resource_data={"CidrBlock": "10.0.0.0/0"},
                secondary_attributes=[{"EnableDnsSupport": {"Value": True}}],
            )
        )
        cwr = CloudWandererResource(urn=urn, resource_data={}, secondary_attributes=[], loader=mock_loader)
        assert cwr.is_inflated is False
        cwr.load()
        assert cwr.is_inflated is True
        assert cwr.cidr_block == "10.0.0.0/0"

    def test_str(self):
        cwr = CloudWandererResource(
            urn=URN.from_string("urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111"),
            resource_data={"CidrBlock": "10.0.0.0/0"},
            secondary_attributes=[{"EnableDnsSupport": {"Value": True}}],
        )

        assert str(cwr) == str(
            "CloudWandererResource("
            "urn=URN(account_id='111111111111', region='eu-west-2', service='ec2', "
            "resource_type='vpc', resource_id_parts=['vpc-11111111']), "
            "subresource_urns=[], "
            "resource_data={'CidrBlock': '10.0.0.0/0'}, secondary_attributes=[{'EnableDnsSupport': {'Value': True}}]"
            ")"
        )

    def test_repr(self):
        cwr = CloudWandererResource(
            urn=URN.from_string("urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111"),
            resource_data={"CidrBlock": "10.0.0.0/0"},
            secondary_attributes=[{"EnableDnsSupport": {"Value": True}}],
        )

        assert repr(cwr) == str(
            "CloudWandererResource("
            "urn=URN(account_id='111111111111', region='eu-west-2', service='ec2', "
            "resource_type='vpc', resource_id_parts=['vpc-11111111']), "
            "subresource_urns=[], "
            "resource_data={'CidrBlock': '10.0.0.0/0'}, secondary_attributes=[{'EnableDnsSupport': {'Value': True}}]"
            ")"
        )

    def test_empty(self):
        """Do not throw when there is no resource data.

        This scenario occurs for some older AWS resources like sns topics as
        their ``describe_`` methods can return no data.
        """
        CloudWandererResource(
            urn=URN.from_string("urn:aws:111111111111:eu-west-2:ec2:vpc:vpc-11111111"),
            resource_data=None,
            secondary_attributes=[],
        )

    def test_subresource(self):
        parent_urn = URN.from_string("urn:aws:111111111111:us-east-1:iam:role:test-role")
        urn = URN.from_string("urn:aws:111111111111:us-east-1:iam:role_policy:test-role/test-policy")
        cwr = CloudWandererResource(urn=urn, resource_data={}, secondary_attributes=[])

        assert cwr.parent_urn == parent_urn
