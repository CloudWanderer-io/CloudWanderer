import unittest

from cloudwanderer.storage_connectors import DynamoDbConnector

from ..helpers import DEFAULT_SESSION


class TestDynamoDBConnector(unittest.TestCase):
    def test_repr(self):
        connector = DynamoDbConnector(boto3_session=DEFAULT_SESSION)
        assert repr(connector) == (
            'DynamoDbConnector(table_name="cloud_wanderer", endpoint_url="None", '
            'boto3_session="Session(region_name=\'eu-west-2\')", client_args="{}, number_of_shards=10)'
        )

    def test_str(self):
        connector = DynamoDbConnector(boto3_session=DEFAULT_SESSION)
        assert str(connector) == "<DynamoDbConnector=cloud_wanderer>"
