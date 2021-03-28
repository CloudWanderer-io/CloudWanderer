import unittest

from cloudwanderer.storage_connectors import DynamoDbConnector

from ..storage_write_generic import StorageWriteTestMixin


class TestStorageDynamoDbWrite(StorageWriteTestMixin, unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connector = DynamoDbConnector()

    def reset_dynamodb_table(self):
        try:
            self.mock_session.resource("dynamodb").Table(name="cloud_wanderer").delete()
        except self.mock_session.client("dynamodb").exceptions.ResourceNotFoundException:
            pass
        finally:
            self.connector.init()

    def setUp(self):
        self.reset_dynamodb_table()
