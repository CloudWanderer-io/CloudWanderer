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

        assert [str(x) for x in self.secondary_attributes_directive.get_cloudwanderer_secondary_attributes()] == [
            "<list_item>ec2<bullet_list><list_item>vpc_enable_dns_support</list_item></bullet_list></list_item>",
            "<list_item>iam<bullet_list><list_item>role_inline_policy_attachments</list_item><list_item>role_managed_policy_attachments</list_item></bullet_list></list_item>",
        ]
