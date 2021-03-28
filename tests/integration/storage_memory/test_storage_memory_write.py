import unittest

from cloudwanderer.storage_connectors import MemoryStorageConnector

from ..storage_write_generic import StorageWriteTestMixin


class TestStorageMemoryWrite(StorageWriteTestMixin, unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connector = MemoryStorageConnector()

    def setUp(self):
        self.connector = MemoryStorageConnector()
