import pandas as pd
import pycurl
from io import BytesIO

from fastor.common.resources import info_wrap, error_wrap


WEBSITES_LIST_PATH = "fastor/resources/top500Domains.csv"
VALIDATED_LIST_PATH = "fastor/resources/validatedDomains.csv"


# Get unvalidated website list
df_unvalid = pd.read_csv(WEBSITES_LIST_PATH)
unvalid_list = list(df_unvalid['Root Domain'])
n_unvalid = len(unvalid_list)

# Create validated empty list
valid_list = []

for i, website in enumerate(unvalid_list):
    b_obj = BytesIO()
    crl = pycurl.Curl()

    # Set URL value
    crl.setopt(crl.URL, website)
    crl.setopt(pycurl.CONNECTTIMEOUT, 7)

    # Write bytes that are utf-8 encoded
    crl.setopt(crl.WRITEDATA, b_obj)

    try:
        # Perform a file transfer
        crl.perform()
        print(f"{i+1}/{n_unvalid}: " + info_wrap(f"{website} exists"))
    except pycurl.error:
        print(f"{i+1}/{n_unvalid}: " + error_wrap(f"{website} doesnt exist"))
    else:
        valid_list.append(website)

    # End curl session
    crl.close()

# Save valid list in validated path
df = pd.DataFrame()
df['website'] = valid_list
df.to_csv(VALIDATED_LIST_PATH)
print(f"\nSaved to {VALIDATED_LIST_PATH}")
