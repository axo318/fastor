import unittest

from fastor.common import log


class LoggingTestCase(unittest.TestCase):

    def test_log(self):
        log.debug("This is a debug message")
        log.info("This is an info message")
        log.warn("This is a warning message")
        log.error("This is an error message")
