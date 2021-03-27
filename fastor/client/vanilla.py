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
CIRCUIT_UPDATE_TIME_S = 10 * 60         # 10 minutes


# Event names
CONSENSUS_UPDATE_EVENT = "consensus_update"
RENEW_CIRCUIT_EVENT = "renew_current_circuit"


@ClientType.register('vanilla')
class VanillaClient(Client):
    def _getScheme(self) -> 'Scheme':
        """ Returns initialized vanilla Tor scheme """
        return VanillaScheme(self, self.tor_handler, GUARD_FP)


class VanillaScheme(Scheme):

    def __init__(self, *args, **kwargs):
        """ Tor Vanilla circuit choosing scheme """
        super().__init__(*args, **kwargs)

    def onStart(self) -> None:
        """ Called when the scheme is starting """
        self.consensus = self.tor_handler.getConsensus()
        self._createNewCurrentCircuit()

    def setUpEvents(self) -> None:
        """ Called when scheme is starting, after onStart """
        # If the consensus was created more than 1 hour ago, then generate event
        def consensus_update_condition():
            return self.consensus.creation_time - time.time() > CONSENSUS_UPDATE_TIME_S
        self.scheduler.registerCondition(consensus_update_condition, CONSENSUS_UPDATE_EVENT)

        # When consensus update event is generated, then update the current consensus
        def consensus_update_event_listener():
            self.consensus = self.tor_handler.getConsensus()
        self.scheduler.addListener(consensus_update_event_listener, CONSENSUS_UPDATE_EVENT)

        # If current circuit was created more than 10 minutes ago, generate event
        def renew_circuit_condition():
            return self.currentCircuit.time_built - time.time() > CIRCUIT_UPDATE_TIME_S
        self.scheduler.registerCondition(renew_circuit_condition, RENEW_CIRCUIT_EVENT)

        def renew_circuit_event_listener():
            self.renewCurrentCircuit()
        self.scheduler.addListener(renew_circuit_event_listener, RENEW_CIRCUIT_EVENT)

    def renewCurrentCircuit(self) -> None:
        """ Renew current circuit (because of possible errors) """
        self._closeCurrentCircuit()
        self._createNewCurrentCircuit()

    def onStop(self) -> None:
        """ Called when scheme is terminating """
        self._closeCurrentCircuit()

    # Private #
    def _createNewCurrentCircuit(self) -> None:
        """ Chooses and constructs a new circuit through Tor. If construction fails, it retries until success. """
        while True:
            circuit_path = self._chooseCircuitPath()
            try:
                self.currentCircuit = self._constructCircuit(circuit_path)
                break
            except TorHandlerException as e:
                print(e)
                self.debug(f"Circuit failed to be constructed. Retrying ...")

    def _chooseCircuitPath(self) -> List[str]:
        descriptors = self.consensus.descriptors
        middle_descriptors = descriptors
        exit_descriptors = [d for d in descriptors if stem.Flag.EXIT in d.flags]

        # Get middles info
        middle_fingerprints = [d.fingerprint for d in middle_descriptors]
        middle_bws = [d.bandwidth for d in middle_descriptors]
        middle_bws_sum = sum(middle_bws)
        middle_p = [bw/middle_bws_sum for bw in middle_bws]

        # Get exits info
        exit_fingerprints = [d.fingerprint for d in exit_descriptors]
        exit_bws = [d.bandwidth for d in exit_descriptors]
        exit_bws_sum = sum(exit_bws)
        exit_p = [bw/exit_bws_sum for bw in exit_bws]

        # Select random middle
        middle_fp = np.random.choice(middle_fingerprints, p=middle_p)

        # Select random exit
        exit_fp = middle_fp
        while exit_fp == middle_fp:
            exit_fp = np.random.choice(exit_fingerprints, p=exit_p)

        path = [self.guard_fingerprint, middle_fp, exit_fp]

        return path

    def _constructCircuit(self, path: List[str]) -> TorCircuit:
        """ Attempts to construct the requested circuit

        :param path: Circuit path
        :raises TorHandlerException
        :return: TorCircuit
        """
        circuit_id = self.tor_handler.createCircuit(path, await_build=True)
        time_build = time.time()
        return TorCircuit(circuit_id, time_build, path)

    def _closeCurrentCircuit(self) -> None:
        if self.currentCircuit:
            self.tor_handler.closeCircuit(self.currentCircuit.circuit_id)



