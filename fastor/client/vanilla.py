from fastor.client.client import Client
from fastor.client.utils import ClientType
from fastor.common import FastorObject


@ClientType.register('vanilla')
class VanillaClient(Client):
    def __init__(self, *args, **kwargs):
        """ Client using vanilla Tor scheme """
        super().__init__(*args, **kwargs)
        self.scheme = VanillaScheme(self)



    def request(self, url: str) -> bytes:
        """ Sends HTTP request to the url provided with an empty query, and returns the response

        :param url: URL to send pycurl to
        :return: bytes object containing the response
        """
        pass


class VanillaScheme(FastorObject):
    def __init__(self, client: Client):
        """ Responsible for scheme-specific logic

        :param client:
        """
        self.client = client
