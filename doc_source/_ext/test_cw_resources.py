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
        results = self.resources_directive.get_cloudwanderer_resources()

        assert (
            results
            == """* :doc:`API Gateway <resource_properties/apigateway>`
    * :class:`RestApis<apigateway.rest_api>`
* :doc:`Lambda <resource_properties/lambda>`
    * :class:`Functions<lambda.function>`
    * :class:`Layers<lambda.layer>`
         * :class:`Layer Versions<lambda.layer.layer_version>`
* :doc:`Secrets Manager <resource_properties/secretsmanager>`
    * :class:`Secrets<secretsmanager.secret>`
"""
        )
