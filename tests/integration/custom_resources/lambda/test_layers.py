import unittest

from cloudwanderer import URN
from cloudwanderer.exceptions import UnsupportedResourceTypeError

from ..helpers import CloudWandererCalls, ExpectedCall, MultipleResourceScenario, NoMotoMock, SingleResourceScenario


class TestLambdaLayers(NoMotoMock, unittest.TestCase):
    layer_payload = {
        "LayerName": "test-layer",
        "LayerArn": "arn:aws:lambda:eu-west-1:123456789012:layer:test-layer",
        "LatestMatchingVersion": {
            "LayerVersionArn": "arn:aws:lambda:eu-west-1:123456789012:layer:test-layer:1",
            "Version": 1,
            "Description": "This is a test layer!",
            "CreatedDate": "2020-10-17T13:18:00.303+0000",
            "CompatibleRuntimes": ["nodejs10.x"],
        },
    }

    layer_version_payload = {
        "LayerVersionArn": "arn:aws:lambda:eu-west-1:123456789012:layer:test-layer:1",
        "Version": 1,
        "Description": "This is a test layer!",
        "CreatedDate": "2020-10-17T13:18:00.303+0000",
        "CompatibleRuntimes": ["nodejs10.x"],
    }

    mock = {
        "lambda": {
            "list_layers.return_value": {
                "Layers": [layer_payload],
            },
            "list_layer_versions.return_value": {"LayerVersions": [layer_version_payload]},
            "get_layer_version.return_value": layer_version_payload,
        }
    }

    single_resource_scenarios = [
        SingleResourceScenario(
            urn=URN.from_string("urn:aws:123456789012:eu-west-1:lambda:layer:test-layer"),
            expected_results=UnsupportedResourceTypeError,
        ),
        SingleResourceScenario(
            urn=URN.from_string("urn:aws:123456789012:eu-west-1:lambda:layer_version:test-layer/1"),
            expected_results=[layer_version_payload],
            expected_call=ExpectedCall(
                "lambda", "get_layer_version", [], {"LayerName": "test-layer", "VersionNumber": 1}
            ),
        ),
    ]
    multiple_resource_scenarios = [
        MultipleResourceScenario(
            arguments=CloudWandererCalls(regions=["eu-west-1"], service_names=["lambda"], resource_types=["layer"]),
            expected_results=[layer_payload, layer_version_payload],
        )
    ]
