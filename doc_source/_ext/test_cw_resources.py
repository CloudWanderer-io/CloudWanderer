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
        results = [str(x) for x in self.resources_directive.get_cloudwanderer_resources()]

        expected_results = [
            "<list_item>API Gateway<bullet_list><list_item>RestApis</list_item></bullet_list></list_item>",
            "<list_item>Lambda<bullet_list><list_item>Functions</list_item></bullet_list></list_item>",
            "<list_item>Secrets Manager<bullet_list><list_item>Secrets</list_item></bullet_list></list_item>",
        ]

        for expected_result in expected_results:
            assert expected_result in results
