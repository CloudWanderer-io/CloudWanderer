import unittest

from supported_resources import CloudWandererResourcesDirective

pytest_plugins = "sphinx.testing.fixtures"


class TestCloudWandererResourcesDirective(unittest.TestCase):
    def setUp(self) -> None:
        self.resources_directive = CloudWandererResourcesDirective(
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

    def test_get_cloudwanderer_resources(self):
        result = self.resources_directive.get_cloudwanderer_resources()

        assert [str(x) for x in result] == [
            "<list_item>apigateway<bullet_list><list_item>RestApis</list_item></bullet_list></list_item>",
            "<list_item>lambda<bullet_list><list_item>Functions</list_item></bullet_list></list_item>",
            "<list_item>secretsmanager<bullet_list><list_item>Secrets</list_item></bullet_list></list_item>",
        ]
