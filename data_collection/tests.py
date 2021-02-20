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


if __name__ == "__main__":
    test_main()
    # test_Controller_readConfig()
    # test_Controller_startTimer()
    # test_CustomLogger_()


