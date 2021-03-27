import time
from io import BytesIO
from typing import List

import stem.control

from fastor.common import FastorObject

try:
    import pycurl
except ImportError:
    pycurl = None
    print("Could not import pycurl")

#
# SOCKS_PORT = 9050
# CONTROL_PORT = 9051
# CONNECTION_TIMEOUT = 15  # timeout before we give up on a circuit


class TorHandler(FastorObject):
    def __init__(self,
                 socks_port: int,
                 control_port: int,
                 connection_timeout: int):
        """ Interface to stem.Controller

        :param socks_port: (default=9050)
        :param control_port: (default=9051)
        :param connection_timeout: seconds before we give up on a circuit (default=15)
        """
        self.socks_port = socks_port
        self.control_port = control_port
        self.connection_timeout = connection_timeout

        self.tor_controller: stem.control.Controller = None

    # Tor controller #
    def attach(self) -> None:
        """ Attaches to Tor running instance.

        :raises TorHandlerException
        """
        self.info("Attaching to Tor instance")
        try:
            self.tor_controller = stem.control.Controller.from_port(port=self.control_port)
        except stem.SocketError as exc:
            self.error(f"Unable to connect to tor on port {self.control_port}: {exc}")
            raise TorHandlerException("Could not connect to Tor instance")
        try:
            self.tor_controller.authenticate()
        except stem.connection.AuthenticationFailure as exc:
            self.error(f"Unable to authenticate: {exc}")
            raise TorHandlerException("Could not authenticate to Tor")
        self.info(f"Tor is running version {self.tor_controller.get_version()}")
        self.tor_controller.set_conf('__LeaveStreamsUnattached', '1')  # leave stream management to us

    def detach(self) -> None:
        """ Detaches from running Tor instance """
        self.info("Detaching from Tor instance")
        if self.tor_controller:
            self.tor_controller.reset_conf('__LeaveStreamsUnattached')
            self.tor_controller.close()

    # Consensus #
    def getConsensus(self) -> 'Consensus':
        """ Retrieves the latest Tor consensus entries and returns them in a list

        :raises TorHandlerException
        :return: List containing all router status entries from the consensus
        """
        time_created = time.time()
        try:
            descs = list(self.tor_controller.get_network_statuses())
            self.debug(f"Retrieved {len(descs)} descriptors from consensus")
            return Consensus(time_created, descs)
        except stem.ControllerError:
            self.warn(f"Could not retrieve network descriptors")
            raise TorHandlerException("Could not retrieve network descriptors")

    # Circuits #
    def createCircuit(self, path, await_build=True) -> str:
        """ Creates a Tor circuit through the specified path

        :param path: List of relay fingerprints
        :param await_build: Wait for the circuit to build or not
        :raises TorHandlerException
        :return: circuit id string
        """
        try:
            circuit_id = self.tor_controller.new_circuit(path, await_build=await_build)
            self.debug(f"Created circuit {circuit_id}")
            return circuit_id
        except stem.ControllerError:
            self.error(f"Circuit build failed through path: {path}")
            raise TorHandlerException()
        except stem.Timeout:
            self.warn(f"Timeout reached for circuit creation: {path}")
            raise TorHandlerException()

    def closeCircuit(self, circuit_id: str) -> None:
        """ Closes the specified circuit

        :param circuit_id: circuit id to be closed
        :return:
        """
        self.debug(f"Closing circuit {circuit_id}")
        try:
            self.tor_controller.close_circuit(circuit_id)
        except stem.InvalidArguments:
            self.warn(f"{circuit_id} did not close, id is unknown")
        except stem.InvalidRequest:
            self.warn(f"{circuit_id} did not close, not enough information was provided")

    # Query #
    def performQuery(self, url: str, circuit_id: str) -> 'QueryResult':
        """ Performs a web query to the requested url, using the specified Tor circuit

        :param url: web url
        :param circuit_id: Tor circuit unique id
        :raises TorHandlerException if something goes wrong while performing the query
        :return: QueryResult object
        """
        self.debug(f"Performing query to {url} though circuit {circuit_id}")

        def attach_stream(stream):
            if stream.status == 'NEW':
                self.tor_controller.attach_stream(stream.id, circuit_id)

        # Set requested circuit as main
        try:
            self.tor_controller.add_event_listener(attach_stream, stem.control.EventType.STREAM)
        except stem.ProtocolError:
            self.error(f"Stream listener failed for query: {url}")
            raise TorHandlerException("Failed to add event listener to tor_controller")

        try:
            start_time = time.time()
            bytes_result = self._send(url)
            time_taken = time.time() - start_time
            return QueryResult(bytes_result.decode("utf-8"), time_taken)
        except QueryException as e:
            raise TorHandlerException("Failed to perform query") from e
        finally:
            # Remove circuit's main status
            self.tor_controller.remove_event_listener(attach_stream)

    def _send(self, url: str) -> bytes:
        """ Sends a web query to url

        :param url:
        :return:
        """
        output = BytesIO()
        query = pycurl.Curl()
        query.setopt(pycurl.URL, url)
        query.setopt(pycurl.PROXY, 'localhost')
        query.setopt(pycurl.PROXYPORT, self.socks_port)
        query.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5_HOSTNAME)
        query.setopt(pycurl.CONNECTTIMEOUT, self.connection_timeout)
        query.setopt(pycurl.WRITEFUNCTION, output.write)
        try:
            query.perform()
            return output.getvalue()
        except pycurl.error as exc:
            # self.warn(f"Unable to reach {url} ({exc})")
            raise QueryException("Query failed") from exc


class QueryResult(FastorObject):
    def __init__(self, web_data: str, time_lapsed: float):
        """ Class holding web query result and time taken to fetch it

        :param web_data: string web data result
        :param time_lapsed: float time taken to fetch web data
        """
        self.web_data = web_data
        self.time_lapsed = time_lapsed

    def __repr__(self):
        s = f"QueryResult(time_lapsed={self.time_lapsed}) [\n"
        s += f"{self.web_data} \n"
        s += "]"
        return s

    def getData(self) -> str:
        """ Returns web data fetched

        :return: str web data
        """
        return self.web_data

    def timeTaken(self) -> float:
        """ Returns time taken to fetch the web result

        :return: float time lapsed
        """
        return self.time_lapsed


class Consensus(FastorObject):
    def __init__(self,
                 creation_time: float,
                 descriptors: List['stem.descriptor.router_status_entry.RouterStatusEntryV3']):
        """ Class holding consensus information

        :param creation_time: Time this consensus was retrieved
        :param descriptors:
        """
        self.creation_time = creation_time
        self.descriptors = descriptors


class TorCircuit(FastorObject):
    def __init__(self, circuit_id: str, time_built: float, path: List[str]):
        """ Class containing circuit information

        :param circuit_id:
        :param time_built:
        :param path:
        """
        self.circuit_id = circuit_id
        self.time_built = time_built
        self.path = path


class TorHandlerException(Exception):
    """ Custom exception signifying there is a communication error with Tor instance. """
    pass


class QueryException(Exception):
    """ Custom exception signifying there was a problem performing a query """
    pass
