from fastor.common import FastorObject
from fastor.events.scheduler import Scheduler
from fastor.torHandler import TorHandler


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
        self.scheduler = Scheduler.retrieve()
        self.tor_handler = TorHandler(socks_port, control_port, connection_timeout)

    def request(self, url: str) -> bytes:
        """ Sends HTTP request to the url provided with an empty query, and returns the response

        :param url: URL to send pycurl to
        :return: bytes object containing the response
        """
        pass
