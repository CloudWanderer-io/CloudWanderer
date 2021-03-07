import unittest

from cloudwanderer.storage_connectors import MemoryStorageConnector


class TestMemoryStorageConnector(unittest.TestCase):
    def test_repr(self):
        connector = MemoryStorageConnector()
        assert repr(connector) == "MemoryStorageConnector()"

    def test_str(self):
        connector = MemoryStorageConnector()
        assert str(connector) == "<MemoryStorageConnector>"
