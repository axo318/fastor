import time
from typing import List

import numpy as np
import stem

from fastor.client.client import Client, Scheme
from fastor.client.utils import ClientType
from fastor.torHandler import TorCircuit, TorHandlerException


# Constants
GUARD_FP = "7A3E534C033E3836BD5AF223B642853C502AB33A"
CONSENSUS_UPDATE_TIME_S = 1 * 60 * 60   # 1 hour
# CIRCUIT_UPDATE_TIME_S = 10 * 60         # 10 minutes
CIRCUIT_UPDATE_TIME_S = 1 * 60          # 1 minute (fast_track)


@ClientType.register('fastor')
class FastorClient(Client):
    def _getScheme(self) -> Scheme:
        """ Returns initialized fastor Tor scheme """
        return FastorScheme(self, self.tor_handler, GUARD_FP)


class FastorScheme(Scheme):
    pass
