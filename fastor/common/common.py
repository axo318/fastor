import datetime
from typing import Callable

from fastor.common.resources import debug_wrap, info_wrap, warning_wrap, error_wrap


# UTILS

def getTimestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d T %H:%M:%S.%f")[:-3]


# CLASSES

class FastorObject:
    """ Common base for all class definitions in fastor """
    def __repr__(self):
        return f"{self.__class__.__name__}()"

    # LOGGING FUNCTIONALITY
    def debug(self, msg):
        self._log(self._constructLog(msg, level="DEBUG", wrapper=debug_wrap))

    def info(self, msg):
        self._log(self._constructLog(msg, level="INFO", wrapper=info_wrap))

    def warn(self, msg):
        self._log(self._constructLog(msg, level="WARNING", wrapper=warning_wrap))

    def error(self, msg):
        self._log(self._constructLog(msg, level="ERROR", wrapper=error_wrap))

    def _constructLog(self, msg: str, level: str, wrapper: Callable) -> str:
        timestamp = wrapper(getTimestamp())
        class_name = self.__class__.__name__
        level_s = wrapper(level)
        return f"[{timestamp}] {class_name} {level_s}: {msg}"

    def _log(self, log):
        print(log)


class Logger(FastorObject):
    """ Singleton logger object for use outside of class space """
    def _constructLog(self, msg: str, level: str, wrapper: Callable) -> str:
        """ Overrides functionality to remove the class name """
        timestamp = wrapper(getTimestamp())
        level_s = wrapper(level)
        return f"[{timestamp}] {level_s}: {msg}"
