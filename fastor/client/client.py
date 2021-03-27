from typing import List

from fastor.common import FastorObject
from fastor.events.scheduler import Scheduler
from fastor.torHandler import TorHandler, QueryResult, TorHandlerException, Consensus, TorCircuit


# CLIENT SUPERCLASS

class Client(FastorObject):
    def __init__(self,
                 socks_port: int = 9050,
                 control_port: int = 9051,
                 connection_timeout: int = 15):
        """ Base Tor client class

        :param socks_port: (default=9050)
        :param control_port: (default=9051)
        :param connection_timeout: seconds before we give up on a circuit (default=15)
        """
        self.tor_handler = TorHandler(socks_port, control_port, connection_timeout)
        self.scheme = self.getScheme()
        self.attached = False

    def attach(self) -> None:
        """ Attaches to background Tor instance

        :raises ClientException if it fails to attach or scheme fails to start
        """
        try:
            self.tor_handler.attach()
        except TorHandlerException as e:
            self.error("Client failed to attach to background Tor instance")
            self.tor_handler.detach()
            raise ClientException("Failed to attach to Tor instance") from e

        try:
            self.scheme.start()
        except TorHandlerException as e:
            self.error("Scheme failed to start")
            raise ClientException("Scheme failed to start") from e

        self.attached = True

    def detach(self) -> None:
        """ Detaches from background Tor instance """
        self.scheme.stop()
        self.tor_handler.detach()
        self.attached = False

    def query(self, url: str) -> QueryResult:
        """ Sends HTTP query to the url provided with an empty query, and returns the response

        :param url: URL to send pycurl to
        :raises ClientException if client not attached to Tor instance
        :return: QueryResult object containing the response
        """
        if self.attached:
            try:
                return self.tor_handler.performQuery(url, self.scheme.getCurrentCircuit())
            except TorHandlerException as e:
                self.error(f"Query to {url} failed")
                raise ClientException("Query has failed") from e
        else:
            self.warn("Query attempted but client is not attached to Tor instance.")
            raise ClientException("Query attempted but client is not attached to Tor instance.")

    # Client-specific methods
    def getScheme(self) -> 'Scheme':
        """ Returns an initialized scheme object, specific to the client_type

        :return: Scheme object
        """
        pass


class Scheme(FastorObject):
    def __init__(self, client: Client, tor_handler: TorHandler, guard_fingerprint: str):
        """ Responsible for scheme-specific logic

        :param client:
        :param tor_handler:
        :param guard_fingerprint Fingerprint of guard node
        """
        self.client = client
        self.tor_handler = tor_handler
        self.guard_fingerprint = guard_fingerprint
        self.scheduler = Scheduler()

        self.consensus: Consensus = None
        self.currentCircuit: TorCircuit = None

    def start(self) -> None:
        """ Initializes scheme """
        self.scheduler.start()
        self.onStart()
        self.setUpEvents()

    def stop(self) -> None:
        """ Stops scheme """
        self.scheduler.stop()
        self.onStop()

    def getCurrentCircuit(self) -> str:
        """ Returns the id of the current circuit

        :return: string id of current circuit
        """
        return self.currentCircuit.circuit_id

    # Scheme-specific methods
    def onStart(self) -> None:
        """ Called after the scheduler has started and before setUpEvents """
        pass

    def setUpEvents(self) -> None:
        """ Sets up conditions and listeners for updating current information """
        pass

    def renewCircuit(self) -> None:
        """ Renew current circuit (because of possible errors) """
        pass

    def onStop(self) -> None:
        """ Called when scheme is terminating """
        pass


class ClientException(Exception):
    """ Exception raised when somethings goes wrong with the client """
    pass
