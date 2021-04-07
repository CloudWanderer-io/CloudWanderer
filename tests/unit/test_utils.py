import logging
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import cloudwanderer
from cloudwanderer.utils import exception_logging_wrapper, load_json_definitions, snake_to_pascal


class TestUtils(unittest.TestCase):
    def test_exception_logging_wrapper(self):
        method = MagicMock(side_effect=Exception("This exception should be logged"))

        with self.assertLogs(logging.getLogger("cloudwanderer.utils"), level="ERROR") as cm:
            exception_logging_wrapper(method)
        assert len(cm.output) == 1
        assert cm.output[0].startswith(
            str("ERROR:cloudwanderer.utils:This exception should be logged\n" "Traceback (most recent call last):\n")
        )

    def test_load_json_definitions(self):
        result = load_json_definitions(Path(cloudwanderer.__file__).parent.joinpath("service_mappings"))
        assert {"iam", "cloudformation", "ec2", "s3", "lambda"}.issubset(set(result.keys()))

    def test_snake_to_pascal(self):
        assert snake_to_pascal("lambda_layer") == "LambdaLayer"
        assert snake_to_pascal("lambda_layer_version") == "LambdaLayerVersion"
