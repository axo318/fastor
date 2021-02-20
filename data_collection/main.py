"""
This script will start collecting bandwidth data from all Tor relays.

-   For each relay in Tor, this will download a specified file from a hosted web server n times and save the TTLB to
    a JSON database

-   configuration:
    -   anchor relay
    -   target file URL
    -   file's size
"""

# IMPORTS

import json
import datetime
from threading import Timer
import hashlib
from io import BytesIO



# VARIABLES

CONFIG_FILE = "config.json"
DATABASE_FILE = "measurements.json"
LOGS_FILE = "logs.txt"
DATA_UPDATE_TIMER_SECONDS = 10

SOCKS_PORT = 9050
CONNECTION_TIMEOUT = 30  # timeout before we give up on a circuit


# CLASSES

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


class CustomConfig(dict):
    def __repr__(self):
        s = ""
        for key in self.keys():
            val = self[key]
            s += f"<> {key}: {val}\n"
        return s


class CustomLogger:
    def __init__(self, path, print_logs=False):
        self.path = path
        self.print_logs = print_logs
        self.cache = list()

    def __call__(self, *args, **kwargs):
        self.add(*args, **kwargs)

    def add(self, msg):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d T %H:%M:%S.%f")
        log = f"[{timestamp}] {msg}\n"
        self.cache.append(log)

        if self.print_logs:
            print(log, end="")

    def dump(self):
        if not self.cache:
            return
        try:
            with open(self.path, "a") as log_file:
                for log in self.cache:
                    log_file.write(log)
            self.cache.clear()
        except Exception as ex:
            print(f"ERROR: There was a Logger error when trying to dump logs to {self.path}. Details below:")
            print(str(ex))


class TorHandler:
    def __init__(self):
        self.socks_port = SOCKS_PORT
        self.conn_timeout = CONNECTION_TIMEOUT
        self.logger = None
        self.url = None
    


class Controller:
    def __init__(self, config_file, database_file, log_file):
        self.config_file = config_file
        self.database_file = database_file
        self.config = CustomConfig()
        self.logger = CustomLogger(log_file)
        self._repeatedTimer = None
        self._lastConfigHash = ""
        self._running = False

    # Public calls
    def run(self):
        self.logger("----------------------------")
        self.logger("INFO: Controller is starting")

        # Start measurements
        self._running = True
        self._startTimer()
        self._measure()

    def stop(self):
        self._running = False
        self._stopTimer()
        self._repeatedEvent()       # Syncing the program state before exiting
        self.logger("INFO: Controller is stopping")
        self.logger("----------------------------")

    # Timer event handling
    def _startTimer(self):
        if self._repeatedTimer is None:
            self._repeatedTimer = RepeatedTimer(DATA_UPDATE_TIMER_SECONDS, self._repeatedEvent)
        else:
            self._repeatedTimer.start()

    def _stopTimer(self):
        if self._repeatedTimer:
            self._repeatedTimer.stop()

    def _repeatedEvent(self):
        self._syncConfig()
        self._syncDatabase()
        self._dumpLogs()

    # Config handling
    def _syncConfig(self):
        try:
            with open(self.config_file, 'rb') as json_file:
                content = json_file.read()
        except Exception as ex:
            self.logger("ERROR: There was a controller error while hashing the configuration file. Details below:")
            self.logger(str(ex))
            return

        # If file hash has changed, update the config
        digest = hashlib.md5(content).hexdigest()
        if digest != self._lastConfigHash:
            self._lastConfigHash = digest
            self._readConfig()
            self._configChanged()

    def _readConfig(self):
        """
        Reads json configuration file and sets self.config elements accordingly
        """
        try:
            with open(self.config_file) as json_file:
                data = json.load(json_file)
                for key in data.keys():
                    self.config[key] = data[key]
        except Exception as ex:
            self.logger("ERROR: There was a controller error while reading the configuration file. Details below:")
            self.logger(str(ex))

    def _configChanged(self):
        self.logger(f"INFO: Config has been updated:\n{self.config}")

    # Database handling
    def _syncDatabase(self):
        pass

    # Log handling
    def _dumpLogs(self):
        self.logger.dump()

    # Measuring
    def _measure(self):

        while self._running:
            pass


def main(verbose=False):
    controller = Controller(CONFIG_FILE, DATABASE_FILE, LOGS_FILE)

    if verbose:
        controller.logger.print_logs = True

    try:
        controller.run()
    except KeyboardInterrupt:
        pass
    except Exception as ex:
        print("An exception has occurred. Details below:")
        print(ex)
    finally:
        controller.stop()


if __name__ == '__main__':
    main()
