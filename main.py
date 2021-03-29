import time
from collections import defaultdict
import os
from typing import Dict, List

import pandas as pd
import json

from fastor.client import getClient

SCHEME = "vanilla"
RESULTS_DIR = "/home/pi/results/"
RESULT_EXT = "results"


def getNewResultsFileName() -> str:
    """ Returns new results file name depending on other files inside the directory

    :return: filename string
    """
    res_files = [x for x in os.listdir(RESULTS_DIR) if x.split('.')[-1] == RESULT_EXT]
    scheme_res_files = [x for x in res_files if SCHEME in x]
    n = len(scheme_res_files)
    return f"{SCHEME}_{n}.{RESULT_EXT}"


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
    df = pd.read_csv('/home/pi/fastor/fastor/resources/validatedDomains.csv')
    web_queue = list(df['website'])
    n_sites = len(web_queue)

    # Create results dictionary [website -> List[float]]
    website_ttlbs = defaultdict(list)

    # Wrap with try in case there is an unexpected exception
    client = getClient(SCHEME)
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
        print("Saving and exiting")
        saveResults(website_ttlbs)

    print("goodbye")
    exit()


if __name__ == "__main__":
    main()
