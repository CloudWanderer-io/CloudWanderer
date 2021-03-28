import unittest

from supported_resources import CloudWandererSecondaryAttributesDirective


class TestCloudWandererSecondaryAttributesDirective(unittest.TestCase):
    def setUp(self) -> None:
        self.secondary_attributes_directive = CloudWandererSecondaryAttributesDirective(
            name="",
            arguments={},
            options=None,
            content=None,
            lineno=1,
            content_offset=None,
            block_text="",
            state=None,
            state_machine=None,
        )

    def test_get_cloudwanderer_secondary_attributes(self):
        result = self.secondary_attributes_directive.get_cloudwanderer_secondary_attributes()
        assert (
            result
            == """* :doc:`EC2 <resource_properties/ec2>`
    * :class:`Vpc<ec2.vpc>`
         * :class:`~ec2.vpc.vpc_enable_dns_support`
* :doc:`IAM <resource_properties/iam>`
    * :class:`Role<iam.role>`
         * :class:`~iam.role.role_inline_policy_attachments`
         * :class:`~iam.role.role_managed_policy_attachments`
"""
        )
