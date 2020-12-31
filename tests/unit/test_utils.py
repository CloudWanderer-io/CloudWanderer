import logging
import unittest
from unittest.mock import MagicMock
from cloudwanderer.utils import exception_logging_wrapper


class TestUtils(unittest.TestCase):

    def test_exception_logging_wrapper(self):
        method = MagicMock(side_effect=Exception('This exception should be logged'))

        with self.assertLogs(logging.getLogger('cloudwanderer.utils'), level='ERROR') as cm:
            exception_logging_wrapper(method)
        assert len(cm.output) == 1
        assert cm.output[0].startswith(str(
            'ERROR:cloudwanderer.utils:This exception should be logged\n'
            'Traceback (most recent call last):\n'
        ))
