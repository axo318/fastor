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

import sys
import json
import datetime
import time
from threading import Timer
import hashlib
from io import BytesIO
import stem.control
from collections import defaultdict

try:
    import pycurl
except ImportError:
    pycurl = None
    print("Could not import pycurl")


# VARIABLES

CONFIG_FILE = "config.json"
STATE_FILE = "state.json"
DATABASE_FILE = "measurements.json"
LOGS_FILE = "logs.txt"
DATA_UPDATE_TIMER_SECONDS = 10

SOCKS_PORT = 9050
CONNECTION_TIMEOUT = 15  # timeout before we give up on a circuit


# UTILS

def getTimestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d T %H:%M:%S.%f")


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

    # NOT NEEDED
    def serialize(self):
        s = ""
        for key in self.keys():
            val = self[key]
            s += f"{key}<>{val},"
        return s[:-1]


class CustomLogger:
    def __init__(self, path, print_logs=False):
        self.path = path
        self.print_logs = print_logs
        self.cache = list()

    def __call__(self, *args, **kwargs):
        self.add(*args, **kwargs)

    def add(self, msg):
        timestamp = getTimestamp()
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


class Measurement:
    def __init__(self, timestamp, relay, times, config):
        self.timestamp = timestamp
        self.relay = relay
        self.times = times
        self.config = config

    def asDict(self):
        anchor = self.config.get('anchor', '')
        file_size = self.config.get('target_file_size_kb', 1)
        d = {'timestamp': self.timestamp,
             'anchor': anchor,
             'file_size_kb': file_size,
             'relay': self.relay,
             'times': self.times
             }
        return d


class Database:
    def __init__(self, measurements_file, state_file, logger):
        self.measurements_file = measurements_file
        self.state_file = state_file
        self.logger = logger

    def getSkipList(self):
        state = self._retrieveState()
        skip_list = state.get('skip', list())

        if not skip_list:
            self.logger("Database INFO: The skip list was not found or is empty")

        return skip_list

    def update(self, skip_list, new_measurements):
        # Save state
        state_dict = {'skip': skip_list}
        try:
            with open(self.state_file, 'w') as file:
                json.dump(state_dict, file)
        except Exception as ex:
            self.logger(f"Database ERROR: Could not save to {self.state_file}")
            self.logger(str(ex))

        # Append measurements to file
        measurement_dicts = [x.asDict() for x in new_measurements]
        measurement_lines = [json.dumps(d)+'\n' for d in measurement_dicts]
        try:
            with open(self.measurements_file, 'a') as file:
                for line in measurement_lines:
                    file.write(line)
        except Exception as ex:
            self.logger(f"Database ERROR: Could not save to {self.measurements_file}")
            self.logger(str(ex))

    def _retrieveState(self):
        state = defaultdict(list)
        try:
            with open(self.state_file, 'r') as state_file:
                data = json.load(state_file)
                for key in data.keys():
                    state[key] = data[key]
        except Exception as ex:
            self.logger(f"Database ERROR: Could not read {self.state_file}, {str(ex)}")
        return state


class MeasurementHandler:
    def __init__(self, logger):
        self.socks_port = SOCKS_PORT
        self.conn_timeout = CONNECTION_TIMEOUT
        self.logger = logger

        self.config = None
        self.anchor = None
        self.url = None
        self.file_size = None
        self.repeats = 5

        self.tor_controller = None
        self.relay_queue = None
        self.skip_list = None

        self.measurement_cache = list()

        self._initialized = False

    # Public methods
    def initialize(self, skip_list):
        if skip_list is None:
            skip_list = list()
        self.skip_list = skip_list
        if self._initTorController():
            if self._buildRelayQueue():
                self._initialized = True
                self.logger(f"MeasurementHandler INFO: Initialized successfully and skipping {len(skip_list)} relays")
                return True
        return False

    def stop(self):
        self.tor_controller.close()
        self.tor_controller = None
        self.skip_list = None
        self._initialized = False

    def updateConfig(self, config):
        self.config = config
        self.anchor = config.get('anchor', None)
        self.url = config.get('target_file_URL', None)
        self.file_size = config.get('target_file_size_kb', None)
        self.repeats = config.get('repeats_per_relay', 10)

    def dumpMeasurementCache(self):
        cache = self.measurement_cache.copy()
        self.measurement_cache.clear()
        return cache

    def measureNext(self):
        if not self._initialized:
            return False

        if not self.relay_queue:
            self.skip_list.clear()
            built = self._buildRelayQueue()
            if not built:
                return False

        next_fp = self.relay_queue.pop()
        self.skip_list.append(next_fp)

        tor_path = [next_fp, self.anchor]
        timestamp = getTimestamp()
        try:
            times_taken = self._scan(tor_path)
        except Exception as ex:
            self.logger(f"MeasurementHandler WARNING: Measurement failed: {next_fp} => {ex}")
            times_taken = []

        if times_taken:
            m = Measurement(timestamp, next_fp, times_taken, self.config)
            self.measurement_cache.append(m)

        return True

    # Tor controller
    def _initTorController(self):
        try:
            self.tor_controller = stem.control.Controller.from_port()
        except stem.SocketError as exc:
            self.logger(f"MeasurementHandler ERROR: Unable to connect to tor on port 9051: {exc}")
            return False
        try:
            self.tor_controller.authenticate()
        except stem.connection.AuthenticationFailure as exc:
            self.logger(f"MeasurementHandler ERROR: Unable to authenticate: {exc}")
            return False
        self.logger(f"MeasurementHandler INFO: Tor is running version {self.tor_controller.get_version()}")
        return True

    # Relays
    def _buildRelayQueue(self):
        fps = self._readConsensus()
        self.relay_queue = [x for x in fps if x not in self.skip_list]

        if self.relay_queue:
            return True
        else:
            self.logger("MeasurementHandler ERROR: Relay queue is empty.")
            return False

    def _readConsensus(self):
        return [desc.fingerprint for desc in self.tor_controller.get_network_statuses()]

    # Query handling
    def _query(self, url):
        """
        Uses pycurl to fetch a site using the proxy on the SOCKS_PORT.
        """
        output = BytesIO()
        query = pycurl.Curl()
        query.setopt(pycurl.URL, url)
        query.setopt(pycurl.PROXY, 'localhost')
        query.setopt(pycurl.PROXYPORT, SOCKS_PORT)
        query.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5_HOSTNAME)
        query.setopt(pycurl.CONNECTTIMEOUT, CONNECTION_TIMEOUT)
        query.setopt(pycurl.WRITEFUNCTION, output.write)
        try:
            query.perform()
            return output.getvalue()
        except pycurl.error as exc:
            self.logger(f"MeasurementHandler WARNING: Unable to reach {url} ({exc})")

    def _scan(self, path):
        circuit_id = self.tor_controller.new_circuit(path, await_build=True)

        def attach_stream(stream):
            if stream.status == 'NEW':
                self.tor_controller.attach_stream(stream.id, circuit_id)

        self.tor_controller.add_event_listener(attach_stream, stem.control.EventType.STREAM)

        times = []
        try:
            self.tor_controller.set_conf('__LeaveStreamsUnattached', '1')  # leave stream management to us
            for i in range(self.repeats):
                start_time = time.time()
                check_page = self._query(self.url)
                time_taken = time.time() - start_time

                if 'van' not in check_page.decode("utf-8"):
                    raise ValueError("Request didn't have the right content")

                times.append(time_taken)

            return times
        finally:
            self.tor_controller.remove_event_listener(attach_stream)
            self.tor_controller.reset_conf('__LeaveStreamsUnattached')


class Controller:
    def __init__(self, config_file, measurements_file, state_file, log_file):
        self.config_file = config_file
        self.config = CustomConfig()
        self.logger = CustomLogger(log_file)
        self.torHandler = MeasurementHandler(self.logger)
        self.database = Database(measurements_file, state_file, self.logger)
        self._repeatedTimer = None
        self._lastConfigHash = ""
        self._running = False

    # Public calls
    def run(self):
        self.logger("----------------------------")
        self.logger("INFO: Controller is starting")

        # Initialize torHandler
        skip_list = self.database.getSkipList()
        if not self.torHandler.initialize(skip_list):
            self.logger(f"ERROR: Tor authentication has failed")
            raise KeyboardInterrupt

        # Start measurements
        self._running = True
        self._startTimer()
        self._measure()

    def stop(self):
        self.logger("INFO: Controller is stopping")
        self.logger("----------------------------")
        self._running = False
        self._stopTimer()
        self._repeatedEvent()       # Syncing the program state before exiting
        self.torHandler.stop()

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
        try:
            with open(self.config_file) as json_file:
                data = json.load(json_file)
                for key in data.keys():
                    self.config[key] = data[key]
        except Exception as ex:
            self.logger("ERROR: There was a controller error while reading the configuration file. Details below:")
            self.logger(str(ex))

    def _configChanged(self):
        self.torHandler.updateConfig(self.config)
        self.logger(f"INFO: Config has been updated:\n{self.config}")

    # Database handling
    def _syncDatabase(self):
        # Dump cached results of torHandler to database and update skip list
        cached_measurements = self.torHandler.dumpMeasurementCache()
        skip_list = self.torHandler.skip_list
        self.database.update(skip_list, cached_measurements)

    # Log handling
    def _dumpLogs(self):
        self.logger.dump()

    # Measuring
    def _measure(self):
        while self._running:
            valid_flag = self.torHandler.measureNext()
            if not valid_flag:
                self.logger(f"ERROR: TorHandler returned a dirty flag. Exiting")
                raise KeyboardInterrupt


# MAIN

def main(verbose=False):
    controller = Controller(CONFIG_FILE, DATABASE_FILE, STATE_FILE, LOGS_FILE)

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
    if len(sys.argv) > 1 and sys.argv[1] == "-v":
        main(True)
    else:
        main()





