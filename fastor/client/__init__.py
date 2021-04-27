from fastor.client.client import Client
from fastor.client.utils import ClientType
from fastor.common import log

# Register imports (For decorators to register client sublcasses)
import fastor.client.vanilla
import fastor.client.fastor


# FACTORY

def getClient(client_type: str = 'fastor', **args) -> 'Client':
    """ Factory method returns an initialized object of the required Client Class

    :param client_type: defines the client Tor scheme
                        Supported: ('vanilla', 'fastor')
    :return:
    """
    ClientSubclass = ClientType.d[client_type]
    DefaultSubclass = ClientType.d['fastor']

    if client_type:
        return ClientSubclass(**args)
    else:
        log.warn(f"Given client_type:'{client_type}' was not recognised. Returning default fastor scheme client.")
        return DefaultSubclass()
