from fastor.client.client import Client
from fastor.client.utils import ClientType


@ClientType.register('fastor')
class FastorClient(Client):
    def __init__(self):
        """ Client using the fastor scheme """

        pass
