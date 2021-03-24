import time
from collections import Callable
from threading import Timer, Thread, Event


class UIDS:
    """ Static class providing a unique, incrementing integer id """
    uid = 0

    @staticmethod
    def getId():
        temp_uid = UIDS.uid
        UIDS.uid += 1
        return temp_uid


class ArgCallable:
    def __init__(self, event_call: Callable, args: list):
        if args is None:
            args = []
        self.event_call = event_call
        self.args = args

    def __call__(self):
        return self.event_call(*self.args)


class RepeatedTimer:
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.function(*self.args, **self.kwargs)    # Call function on initialization
        self.start()                                # Start timer for subsequent calls

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False


class RepeatingThread:
    def __init__(self, interval, function, *args, **kwargs):
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.running = Event()
        self.thread = None
        self.start()

    def _run(self):
        while self.running.isSet():
            self.function(*self.args)
            time.sleep(self.interval)

    def start(self):
        if not self.running.isSet():
            self.running.set()
            self.thread = Thread(target=self._run)
            self.thread.start()

    def stop(self):
        self.running.clear()
