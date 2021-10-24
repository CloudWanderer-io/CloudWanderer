import unittest

import boto3

from cloudwanderer.storage_connectors import DynamoDbConnector


class TestDynamoDBConnector(unittest.TestCase):
    def test_repr(self):
        connector = DynamoDbConnector(
            boto3_session=boto3.Session(aws_access_key_id="1", aws_secret_access_key="1", region_name="eu-west-2")
        )
        assert repr(connector) == (
            'DynamoDbConnector(table_name="cloud_wanderer", endpoint_url="None", '
            'boto3_session="Session(region_name=\'eu-west-2\')", client_args="{}, number_of_shards=10)'
        )

    def test_str(self):
        connector = DynamoDbConnector(
            boto3_session=boto3.Session(aws_access_key_id="1", aws_secret_access_key="1", region_name="eu-west-2")
        )
        assert str(connector) == "<DynamoDbConnector=cloud_wanderer>"
