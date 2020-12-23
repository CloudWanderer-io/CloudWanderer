import logging
import unittest
from unittest.mock import MagicMock
from cloudwanderer.utils import exception_logging_wrapper


class TestUtils(unittest.TestCase):

    def test_exception_logging_wrapper(self):
        method = MagicMock(side_effect=Exception('This exception should be logged'))

        with self.assertLogs(logging.getLogger(), level='ERROR') as cm:
            exception_logging_wrapper(method)
        self.assertEqual(cm.output, ['ERROR:root:This exception should be logged'])
