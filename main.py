import time
from collections import defaultdict
import os
from typing import Dict, List

import pandas as pd
import json

from fastor.client import getClient
from fastor.common import log
from fastor.common.resources import VALIDATED_DOMAINS_CSV_PATH

# VARIABLES
MEAN = "mean"
VARIANCE = "variance"
STD = "standard deviation"
MEAD = "mean absolute deviation"
MAD = "median absolute deviation"


# OPTIONS
SCHEME = "fastor"
POOL_SIZE = 5
PA_PARAMETER = 0.0
SCORE_METRIC = MAD

RESULTS_DIR = "/home/pi/results/"
RESULT_EXT = "results"


def getNewResultsFileName() -> str:
    """ Returns new results file name depending on other files inside the directory

    :return: filename string
    """
    res_files = [x for x in os.listdir(RESULTS_DIR) if x.split('.')[-1] == RESULT_EXT]
    scheme_res_files = [x for x in res_files if SCHEME in x]

    if SCHEME == "fastor":
        n = len([x for x in scheme_res_files if str(PA_PARAMETER) in x and str(POOL_SIZE) in x])
        name = f"{SCHEME}_PA{PA_PARAMETER}_POOL{POOL_SIZE}_{n}.{RESULT_EXT}"
    else:
        n = len(scheme_res_files)
        name = f"{SCHEME}_{n}.{RESULT_EXT}"
    return name


def saveResults(website_ttlbs: Dict[str, List[float]]):
    """ Saves results collected in a new results file inside the res_directory

    :param website_ttlbs: TTLB measurements of websites
    :return:
    """
    if website_ttlbs.keys():
        file_name = getNewResultsFileName()
        file_path = os.path.join(RESULTS_DIR, file_name)
        with open(file_path, 'w+') as f:
            f.write(json.dumps(website_ttlbs))


def main():
    # Get top websites
    df = pd.read_csv(VALIDATED_DOMAINS_CSV_PATH)
    web_queue = list(df['website'])
    n_sites = len(web_queue)

    # Create results dictionary [website -> List[float]]
    website_ttlbs = defaultdict(list)

    # Init client with options
    if SCHEME == "fastor":
        client = getClient(SCHEME,
                           pool_size=POOL_SIZE,
                           pa_parameter=PA_PARAMETER,
                           score_metric=SCORE_METRIC)
        log.info("Starting fastor scheme with the following settings:")
        log.info(f" POOL_SIZE: {POOL_SIZE}")
        log.info(f" PA_PARAMETER: {PA_PARAMETER}")
        log.info(f" SCORE_METRIC: {SCORE_METRIC}")
    else:
        client = getClient(SCHEME)
        log.info(f"Starting {SCHEME} scheme")

    try:
        # Init client
        client.attach()

        while True:

            # Loop through websites
            for i in range(n_sites):
                web_site_url = web_queue[i]

                # Perform query and append time lapsed
                try:
                    res = client.query(web_site_url)
                    website_ttlbs[web_site_url].append(res.time_lapsed)
                except Exception:
                    print(f"Failed to query: {web_site_url}. Continuing")

                print(f"------> Done {i+1}/{n_sites}\n")

    except KeyboardInterrupt:
        print(f"KeyboardInterrupt. Exiting")
    except Exception as e:
        print(f"Exception occurred {e}. Exiting")
    finally:
        client.detach()
        print(f"Parameters were: "
              f"pool_size={POOL_SIZE}, "
              f"pa_parameter={PA_PARAMETER}, "
              f"score_metric={SCORE_METRIC}")
        print("Saving and exiting...")
        saveResults(website_ttlbs)

    print("Goodbye")
    exit()


if __name__ == "__main__":
    main()
