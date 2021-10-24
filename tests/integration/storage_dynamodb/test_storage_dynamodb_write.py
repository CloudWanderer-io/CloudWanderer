import unittest

from cloudwanderer.storage_connectors import DynamoDbConnector

from ..storage_write_generic import StorageWriteTestMixin

# from moto import mock_dynamodb2


class TestStorageDynamoDbWrite(StorageWriteTestMixin, unittest.TestCase):
    @classmethod
    def setupClass(cls):
        super().setupClass()
        # cls.mocks.append(mock_dynamodb2().start())
        cls.connector = DynamoDbConnector()

    def reset_dynamodb_table(self):
        try:
            self.mock_session.resource("dynamodb").Table(name="cloud_wanderer").delete()
        except self.mock_session.client("dynamodb").exceptions.ResourceNotFoundException:
            pass
        finally:
            self.connector.init()

    def setUp(self):
        self.reset_dynamodb_table()
