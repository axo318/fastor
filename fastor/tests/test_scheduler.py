import unittest
import time

from fastor.events.scheduler import Scheduler


class SchedulerTestCase(unittest.TestCase):

    def test_Scheduler(self):
        scheduler = Scheduler()
        scheduler.start()

        test_list = []
        start_time = [time.time()]
        interval_invalid = 10

        # Create event and callbacks
        LIST_INVALID_EVENT = 'LIST_INVALID'

        def listInvalidGenerator():
            now = time.time()
            if now - start_time[0] > interval_invalid:
                return True
            else:
                return False

        def listInvalidListener():
            test_list.append(str(len(test_list)))
            print(f"list is {test_list}")
            start_time[0] = time.time()

        scheduler.registerCondition(listInvalidGenerator, LIST_INVALID_EVENT)
        scheduler.addListener(listInvalidListener, LIST_INVALID_EVENT)

        print('sleeping')
        time.sleep(45)

        print('done')
        scheduler.stop()
