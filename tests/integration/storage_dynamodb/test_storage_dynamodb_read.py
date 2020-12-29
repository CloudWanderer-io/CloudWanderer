import unittest
from ..storage_read_generic import StorageReadTestMixin
from cloudwanderer.storage_connectors.dynamodb import DynamoDbConnector, IndexNotAvailableException


class TestStorageMemoryRead(StorageReadTestMixin, unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connector_class = DynamoDbConnector
        self.valid_exceptions = (IndexNotAvailableException)
