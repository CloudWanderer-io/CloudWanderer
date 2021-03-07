import unittest

import boto3
from botocore.model import Shape

from cloudwanderer.boto3_helpers import _clean_boto3_metadata, get_shape

from ..helpers import get_default_mocker
from ..mocks import add_infra


class TestBoto3Helpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        get_default_mocker().start_general_mock()
        add_infra()

    @classmethod
    def tearDownClass(cls):
        get_default_mocker().stop_general_mock()

    def test_get_shape(self):
        result = get_shape(boto3.resource("iam").Role("test-role"))

        assert isinstance(result, Shape)

    def test__clean_boto3_metadata(self):
        result = _clean_boto3_metadata(
            boto3_metadata={
                "ShouldIBeHere": "Yes",
                "ResponseMetadata": {"ShouldIBeHere": "No"},
            }
        )

        assert result == {"ShouldIBeHere": "Yes"}
