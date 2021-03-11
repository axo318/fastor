from typing import Callable

from fastor.common import FastorObject


class EventScheduler(FastorObject):
    def __init__(self):
        """ System for registering/de-registering event callbacks """
        pass

    def registerListener(self, func: Callable, event_type: str):
        pass



class WorkerThread(FastorObject):
    """ Singleton object containing a dedicated thread for performing jobs """
    pass
