import datetime
import hashlib

from data_collection.main import *


def test_main():
    main(verbose=True)


def test_Controller_readConfig():
    controller = Controller("config.json", "", "logs.txt")
    controller._readConfig()
    print(controller.config)


def test_Controller_startTimer():
    controller = Controller("config.json", "", "logs.txt")
    controller.logger.print_logs = True
    controller._startTimer()


def test_CustomLogger_():
    logger = CustomLogger("logs.txt")
    logger("First Message")
    logger("Second Message")
    logger.dump()
    logger("Third Message")
    logger.dump()


# DATABASE TESTS
def test_Database_getSkipList():
    db = Database('measurements.json', 'state.json', CustomLogger('logs.txt', print_logs=True))
    skip_list = db.getSkipList()
    print(skip_list)


def test_Database_update():
    db = Database('measurements.json', 'state.json', CustomLogger('logs.txt', print_logs=True))

    # Create new skip list
    new_skip = ['relay1', 'relay2', 'relay3']

    # Create custom config object
    config = CustomConfig()
    config['anchor'] = 'anchor1'
    config['target_file_URL'] = "http://a5a7aram.ddns.net:8000/file.txt"
    config['target_file_size_kb'] = 1
    config['repeats_per_relay'] = 10

    # Create 2 new measurements
    measurement1 = Measurement('time1', 'relay1', [1,2,3], config)
    measurement2 = Measurement('time2', 'relay2', [2,3,4], config)
    new_measurements = [measurement1, measurement2]

    # Save them to database
    db.update(new_skip, new_measurements)


if __name__ == "__main__":
    # test_main()
    # test_Controller_readConfig()
    # test_Controller_startTimer()
    # test_CustomLogger_()
    test_Database_getSkipList()
    test_Database_update()
