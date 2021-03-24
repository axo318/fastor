from fastor.common import log
from fastor.common import FastorObject
from fastor.client.utils import ClientType


# FACTORY

def getClient(client_type: str = 'fastor') -> 'Client':
    """ Factory method returns an initialized object of the required Client Class

    :param client_type: defines the client Tor scheme
                        Supported: ('vanilla', 'fastor')
    :return:
    """
    ClientSubclass = ClientType.d[client_type]

    if client_type:
        return ClientSubclass()
    else:
        log.warn(f"Given client_type:'{client_type}' was not recognised. Returning default fastor scheme client.")
        return FastorClient()


# CLIENT CLASSES

class Client(FastorObject):
    """ Base class for all client types """
    def request(self, url: str) -> bytes:
        """ Sends HTTP request to the url provided with an empty query.

        :param url: URL to send pycurl to
        :return: bytes object containing the response
        """
        pass


@ClientType.register('vanilla')
class VanillaClient(Client):
    """ Client using vanilla Tor """
    pass


@ClientType.register('fastor')
class FastorClient(Client):
    """ Client using the fastor scheme """
    pass
