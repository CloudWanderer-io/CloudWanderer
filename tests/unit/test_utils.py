from unittest.mock import MagicMock

from cloudwanderer.utils import camel_to_snake, exception_logging_wrapper, snake_to_pascal


def test_exception_logging_wrapper(caplog):
    method = MagicMock(side_effect=Exception("This exception should be logged"))

    exception_logging_wrapper(method)
    assert "This exception should be logged\n" "Traceback (most recent call last):\n" in caplog.text


def test_snake_to_pascal():
    assert snake_to_pascal("lambda_layer") == "LambdaLayer"
    assert snake_to_pascal("lambda_layer_version") == "LambdaLayerVersion"


def test_camel_to_snake():
    assert camel_to_snake("camelToSnake") == "CAMEL_TO_SNAKE"
    assert camel_to_snake("camelToSnake", False) == "camel_to_snake"
