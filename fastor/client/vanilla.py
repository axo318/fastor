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


# Event names
CONSENSUS_UPDATE_EVENT = "CONSENSUS_UPDATE_EVENT"
RENEW_CIRCUIT_EVENT = "RENEW_CIRCUIT_EVENT"


@ClientType.register('vanilla')
class VanillaClient(Client):
    def _getScheme(self) -> Scheme:
        """ Returns initialized vanilla Tor scheme """
        return VanillaScheme(self, self.tor_handler, GUARD_FP)


class VanillaScheme(Scheme):
    """ Tor Vanilla circuit choosing scheme """

    def onStart(self) -> None:
        """ Called when the scheme is starting """
        self.consensus = self.tor_handler.getConsensus()
        self._createNewCurrentCircuit()

    def setUpEvents(self) -> None:
        """ Called when scheme is starting, after onStart """
        # If the consensus was created more than 1 hour ago, then generate event
        def consensus_update_condition():
            return time.time() - self.consensus.creation_time > CONSENSUS_UPDATE_TIME_S
        self.scheduler.registerCondition(consensus_update_condition, CONSENSUS_UPDATE_EVENT)

        # When consensus update event is generated, then update the current consensus
        def consensus_update_event_listener():
            self.consensus = self.tor_handler.getConsensus()
        self.scheduler.addListener(consensus_update_event_listener, CONSENSUS_UPDATE_EVENT)

        # If current circuit was created more than 10 minutes ago, generate event
        def renew_circuit_condition():
            res = time.time() - self.currentCircuit.time_built > CIRCUIT_UPDATE_TIME_S
            return res
        self.scheduler.registerCondition(renew_circuit_condition, RENEW_CIRCUIT_EVENT)

        def renew_circuit_event_listener():
            self.renewCurrentCircuit()
        self.scheduler.addListener(renew_circuit_event_listener, RENEW_CIRCUIT_EVENT)

    def renewCurrentCircuit(self) -> None:
        """ Renew current circuit (because of possible errors) """
        self.thread_lock.acquire()
        try:
            # THREAD SAFE CODE #
            self._closeCurrentCircuit()
            self._createNewCurrentCircuit()
            # # # # # # # # # #
        finally:
            self.thread_lock.release()

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
        # Select random middle
        middle_fp = np.random.choice(self.consensus.middle_fingerprints, p=self.consensus.middle_probabilities)

        # Select random exit
        exit_fp = middle_fp
        while exit_fp == middle_fp:
            exit_fp = np.random.choice(self.consensus.exit_fingerprints, p=self.consensus.exit_probabilities)

        return [self.guard_fingerprint, middle_fp, exit_fp]

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



