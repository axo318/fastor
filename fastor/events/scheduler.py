from collections import defaultdict
from typing import Callable, Dict, List, Any

from fastor.common import FastorObject
from fastor.events.utils import UIDS, ArgCallable, RepeatingThread

EVENT_CONDITION_INTERVAL = 2    # Interval between event generation checks (seconds)


class Scheduler(FastorObject):
    # Singleton #
    _INSTANCE: 'Scheduler' = None

    @staticmethod
    def retrieve() -> 'Scheduler':
        """ Static method call to retrieve the singleton Scheduler instance

        :return: Scheduler singleton object
        """
        if Scheduler._INSTANCE is None:
            Scheduler._INSTANCE = Scheduler()
        return Scheduler._INSTANCE

    # Constructor #
    def __init__(self):
        """ System for registering/de-registering event callbacks """
        self.schedule = Schedule()
        self.event_thread = EventThread(scheduler=self)

    # Public #

    # Control and event methods (used by user-code)
    def start(self) -> None:
        """ Initializes event thread """
        self.info("Scheduler is initiating.")
        self.event_thread.start()

    def stop(self) -> None:
        """ Stops event thread """
        self.info("Scheduler is terminating.")
        self.event_thread.stop()

    def registerCondition(self, condition: Callable[[Any], bool], event_type: str, args=None) -> int:
        """ Registers input condition call for 'event_type' event generation.

        :param condition: call which returns True if an event of 'event_type' should be generated
        :param event_type: type of event to link the condition call to
        :param args: arguments for the condition call
        :return: condition id, can be used to remove the condition
        """
        if args is None:
            args = []
        uid = self.schedule.registerCondition(condition, event_type, args)
        self.debug(f"Generator was added for event {event_type} with condition_id: {uid}")
        return uid

    def addListener(self, listener: Callable[[Any], None], event_type: str, args=None) -> int:
        """ Subscribes listener callback to be called when an event of 'event_type' is generated.

        :param listener: callback when 'event_type' event is generated
        :param event_type: type of event this listener subscribes to
        :param args: arguments for the listener callback
        :return: listener id, can be used to de-subscribe the listener
        """
        if args is None:
            args = []
        uid = self.schedule.addListener(listener, event_type, args)
        self.debug(f"Listener was added for event {event_type} with listener_id: {uid}")
        return uid

    def removeCondition(self, condition_id: int) -> None:
        """ Removes the condition pointed by the condition_id. If id does not exist, this does nothing.

        :param condition_id: unique id for the condition
        :return:
        """
        self.debug(f"Removing condition with id: {condition_id}")
        self.schedule.removeCondition(condition_id)

    def removeListener(self, listener_id: int) -> None:
        """ De-subscribes the listener pointed by the listener_id. If id does not exist, this does nothing

        :param listener_id: unique id for the listener
        :return:
        """
        self.debug(f"Removing listener with id: {listener_id}")
        self.schedule.removeListener(listener_id)

    # Interface methods for EventThread
    def generateEvent(self, event_type: str) -> None:
        """ Generates an event of 'event_type'

        Called by event thread when events must be generated

        :param event_type: Type of event to generate
        :return:
        """
        self.debug(f"{event_type} event was generated.")
        for listener in self.schedule.getEventListeners(event_type):
            listener()

    def getConditionCheckList(self) -> Dict[str, List[ArgCallable]]:
        """ Returns all registered conditions with their associated event types.

        Called by event thread when checking which events to generate.

        :return: Dictionary with all events and generators
        """
        return self.schedule.getAllConditions()


class Schedule(FastorObject):
    def __init__(self):
        """ Object responsible for storing all generators and listeners for each type of event """
        self.event_condition_ids: Dict[str, List[int]] = defaultdict(list)  # event_type: List[condition_ids]
        self.condition_id_map: Dict[int, ArgCallable] = defaultdict()       # condition_id: ArgCallable
        self.event_listener_ids: Dict[str, List[int]] = defaultdict(list)   # event_type: List[listener_ids]
        self.listener_id_map: Dict[int, ArgCallable] = defaultdict()        # listener_id: ArgCallable

        # Maintained for faster event condition checking
        self.live_conditions: Dict[str, List[ArgCallable]] = defaultdict(list)

    # Public #
    def registerCondition(self, condition: Callable[[Any], bool], event_type: str, args: list) -> int:
        """ Registers a callable which returns true if the desired event should be generated.

        This is going to be checked in the event thread every EVENT_CONDITION_INTERVAL seconds.

        :param condition: Callable returning a boolean signifying whether to generate an event of 'event_type'.
        :param event_type: Event name.
        :param args: List of arguments to be passed in the condition callable.
        :return: unique id for this condition. This can be used to remove this condition.
        """
        condition_id = UIDS.getId()
        condition_callable = ArgCallable(condition, args)
        self.event_condition_ids[event_type].append(condition_id)
        self.condition_id_map[condition_id] = condition_callable
        self._updateConditions()
        return condition_id

    def removeCondition(self, condition_id: int) -> None:
        """ Removes the condition associated with the input id.

        :param condition_id: Unique condition id.
        :return:
        """
        self.condition_id_map.pop(condition_id)
        self._updateConditions()

    def addListener(self, listener: Callable[[Any], None], event_type: str, args: list) -> int:
        """ Subscribes the listener to the 'event_type' event.

        The input listener callable will be called every time an 'event_type' event is generated.

        :param listener: Callable with void return type.
        :param event_type: Name of event to subscribe to.
        :param args: List of arguments to be passed to the listener callable.
        :return:
        """
        gen_id = UIDS.getId()
        event_callback = ArgCallable(listener, args)
        self.event_listener_ids[event_type].append(gen_id)
        self.listener_id_map[gen_id] = event_callback
        return gen_id

    def removeListener(self, listener_id: int) -> None:
        """ Removes listener associated with the unique listener_id.

        :param listener_id: unique id.
        :return:
        """
        self.listener_id_map.pop(listener_id)

    def getAllConditions(self) -> Dict[str, List[ArgCallable]]:
        """ Returns a dictionary containing all events and every condition associated with them.

        :return: Dictionary with all condition callables and their events.
        """
        return self.live_conditions

    def getEventConditions(self, event_type: str) -> List[ArgCallable]:
        """ Returns a list of conditions associated with the given event.

        :param event_type: Name of event.
        :return: List with condition callables.
        """
        return [self.condition_id_map[uid] for uid in self.event_condition_ids[event_type]
                if self.condition_id_map[uid]]

    def getEventListeners(self, event_type) -> List[ArgCallable]:
        """ Returns a list of listener associated with the given event.

        :param event_type: Name of event.
        :return: List with listener callables.
        """
        return [self.listener_id_map[uid] for uid in self.event_listener_ids[event_type]
                if self.listener_id_map[uid]]

    # Private #
    def _updateConditions(self) -> None:
        """ Caches live conditions for faster accessing """
        self.live_conditions = {event_type: [self.condition_id_map[uid] for uid in uids if self.condition_id_map[uid]]
                                for event_type, uids in self.event_condition_ids.items()}


class EventThread(FastorObject):
    def __init__(self, scheduler: Scheduler):
        """ Thread which generates and deals with events """
        self.scheduler = scheduler
        self.repeatedTimer = None

    # Public
    def start(self):
        """ Starts event handling thread as a timed, recurring event which runs every EVENT_CONDITION_INTERVAL seconds
        """
        if self.repeatedTimer is None:
            # self.repeatedTimer = RepeatedTimer(EVENT_CONDITION_INTERVAL, self._threadWork)
            self.repeatedTimer = RepeatingThread(EVENT_CONDITION_INTERVAL, self._threadWork)
        else:
            self.repeatedTimer.start()

    def stop(self):
        """ Stops event handling thread """
        if self.repeatedTimer:
            self.repeatedTimer.stop()

    # Private
    def _threadWork(self):
        """ Thread code which runs every EVENT_CONDITION_INTERVAL seconds
        It checks and generates events """
        event_queue = []

        # Check all event conditions and add events-to-be-generated to event_queue
        for event, conditions in self.scheduler.getConditionCheckList().items():
            for condition in conditions:
                if condition():
                    event_queue.append(event)
                    break

        # Generate events from queue
        for event in event_queue:
            self.scheduler.generateEvent(event)
