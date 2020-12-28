import unittest
from ..storage_read_generic import TestStorageRead
from cloudwanderer.storage_connectors.memory import MemoryStorageConnector


class TestStorageMemoryRead(TestStorageRead, unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connector_class = MemoryStorageConnector
