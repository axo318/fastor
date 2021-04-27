import time
from typing import List

import numpy as np
from numpy.random import random_sample
import pandas as pd
import stem

from fastor.client.client import Client, Scheme
from fastor.client.utils import ClientType
from fastor.torHandler import TorCircuit, TorHandlerException
from fastor.common.resources import RELAY_SCORES_CSV_PATH

# Constants
GUARD_FP = "7A3E534C033E3836BD5AF223B642853C502AB33A"
CONSENSUS_UPDATE_TIME_S = 1 * 60 * 60  # 1 hour
# CIRCUIT_UPDATE_TIME_S = 10 * 60         # 10 minutes
CIRCUIT_UPDATE_TIME_S = 1 * 60  # 1 minute (fast_track)

# DataFrame columns
RELAY = 'relay'
MEAN = "mean"
VARIANCE = "variance"
STD = "standard deviation"
MEAD = "mean absolute deviation"
MAD = "median absolute deviation"

# Default values
POOL_SIZE_DEFAULT = 5
PA_PARAMETER = 0.5
SCORE_METRIC_DEFAULT = MEAN

# Event names
CONSENSUS_UPDATE_EVENT = "CONSENSUS_UPDATE_EVENT"
RENEW_CIRCUIT_EVENT = "RENEW_CIRCUIT_EVENT"


@ClientType.register('fastor')
class FastorClient(Client):
    def __init__(self,
                 pool_size=POOL_SIZE_DEFAULT,
                 pa_parameter=PA_PARAMETER,
                 score_metric=SCORE_METRIC_DEFAULT):
        self.pool_size = int(pool_size)
        self.pa_parameter = float(pa_parameter)
        self.score_metric = score_metric
        super().__init__()

    def _getScheme(self) -> Scheme:
        """ Returns initialized fastor Tor scheme """
        relay_history = pd.read_csv(RELAY_SCORES_CSV_PATH).set_index(RELAY)
        return FastorScheme(relay_history,
                            self.pool_size,
                            self.pa_parameter,
                            self.score_metric,
                            self,
                            self.tor_handler,
                            GUARD_FP)


class FastorScheme(Scheme):
    def __init__(self,
                 relay_history: pd.DataFrame,
                 pool_size: int,
                 pa_parameter: float,
                 score_metric: str,
                 *args,
                 **kwargs):
        """
        :param relay_history: DataFrame containing relay statistics
        :param pool_size: Size of relay pool that we randomly construct from consensus
        :param pa_parameter: Performance-Anonymity parameter (float)
                                1 => focus solely on performance
                                0 => focus solely on anonymity
        :param args: Scheme arguments
        :param kwargs: Scheme arguments
        """
        super().__init__(*args, **kwargs)
        self.relay_history = relay_history
        self.pool_size = pool_size
        self.pa_parameter = pa_parameter
        self.score_metric = score_metric

        self.middle_pool = []
        self.exit_pool = []

    def onStart(self) -> None:
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
        self.thread_lock.acquire()
        try:
            self._closeCurrentCircuit()
            self._createNewCurrentCircuit()
        finally:
            self.thread_lock.release()

    def onStop(self) -> None:
        self._closeCurrentCircuit()

    # Private #
    def _createNewCurrentCircuit(self) -> None:
        while True:
            circuit_path = self._chooseCircuitPath()
            try:
                self.currentCircuit = self._constructCircuit(circuit_path)
                break
            except TorHandlerException as e:
                self.debug(f"Circuit failed to be constructed ({e}). Retrying ...")

    def _chooseCircuitPath(self) -> List[str]:
        self.info("Resetting relay pool...")
        #
        # Choose relay pool with probability of reusing the previously first relay
        new_middle_pool = set()
        new_exit_pool = set()

        # Possibly carry-forward the previously used relay
        if self.middle_pool:
            choice_middle = random_sample()
            choice_exit = random_sample()
            if choice_middle < self.pa_parameter:
                new_middle_pool.add(self.middle_pool[0])
                self.debug("Middle relay was carried forward")
            if choice_exit < self.pa_parameter:
                new_exit_pool.add(self.exit_pool[0])
                self.debug("Exit relay was carried forward")

        # Fill the remaining pool slots using standard Tor bw-weighted choices from consensus
        while len(new_middle_pool) < self.pool_size:
            rand_middle_fp = np.random.choice(self.consensus.middle_fingerprints, p=self.consensus.middle_probabilities)
            new_middle_pool.add(rand_middle_fp)
        while len(new_exit_pool) < self.pool_size:
            rand_exit_fp = np.random.choice(self.consensus.exit_fingerprints, p=self.consensus.exit_probabilities)
            new_exit_pool.add(rand_exit_fp)

        #
        # Retrieve the relay scores and order the queue (lower score is better)
        self.info("Calculating scores...")
        middle_scores = {fp: self._getFpScore(fp) for fp in new_middle_pool}
        exit_scores = {fp: self._getFpScore(fp) for fp in new_exit_pool}
        self.debug(f"Middles' scores: {middle_scores}")
        self.debug(f"Exits' scores: {exit_scores}")
        self.middle_pool = sorted(middle_scores.keys(), key=lambda x: middle_scores[x])
        self.exit_pool = sorted(exit_scores.keys(), key=lambda x: exit_scores[x])
        self.debug(f"Relays were chosen. (Lowest is the best)")
        self.debug(f"    1) Middle: score={middle_scores[self.middle_pool[0]]}, {self.middle_pool[0]}")
        self.debug(f"    2) Exit: score={exit_scores[self.exit_pool[0]]}, {self.exit_pool[0]}")
        #
        # Select the first middle/exit and return the guard, middle, exit path
        return [self.guard_fingerprint, self.middle_pool[0], self.exit_pool[0]]

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

    def _getFpScore(self, fp) -> float:
        """ Retrieves the score of the relay using history data

        :param fp:
        :return:
        """
        try:
            score = float(self.relay_history.loc[fp][self.score_metric])
        except KeyError:
            score = self.relay_history[self.score_metric].mean()
        return score
