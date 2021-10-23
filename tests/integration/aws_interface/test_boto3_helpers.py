import unittest

from cloudwanderer.aws_interface.boto3_helpers import _clean_boto3_metadata

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

    def test__clean_boto3_metadata(self):
        result = _clean_boto3_metadata(
            boto3_metadata={
                "ShouldIBeHere": "Yes",
                "ResponseMetadata": {"ShouldIBeHere": "No"},
            }
        )

        assert result == {"ShouldIBeHere": "Yes"}
