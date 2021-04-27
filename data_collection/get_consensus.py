# Collect consensus data and put it in a csv

import stem.control
import pandas as pd


with stem.control.Controller.from_port() as controller:
    controller.authenticate()
    
    statuses = list(controller.get_network_statuses())
    f = statuses[0]
    relay_fingerprints = [desc.fingerprint for desc in statuses]
    print(len(relay_fingerprints))
    relay_bws = [desc.bandwidth for desc in statuses]
    print(len(relay_bws))
    
    df = pd.DataFrame()
    df["relay"] = relay_fingerprints
    df["bandwidth"] = relay_bws
    
    df.to_csv('last_consensus.csv', index=False)