#########
# PATHS #
#########
import os

_file_dir = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(_file_dir, '..')

RESOURCES_DIR = os.path.join(ROOT_DIR, "resources")

RELAY_SCORES_CSV_PATH = os.path.join(RESOURCES_DIR, 'relay_scores.csv')
VALIDATED_DOMAINS_CSV_PATH = os.path.join(RESOURCES_DIR, 'validatedDomains.csv')


##########
# COLORS #
##########

HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKCYAN = '\033[96m'
OKGREEN = '\033[92m'
CWARNING = '\033[93m'
CFAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'


################
# LOG VARIANTS #
################
def debug_wrap(s): return f"{BOLD}{OKCYAN}{s}{ENDC}"
def info_wrap(s): return f"{BOLD}{OKGREEN}{s}{ENDC}"
def warning_wrap(s): return f"{BOLD}{CWARNING}{s}{ENDC}"
def error_wrap(s): return f"{BOLD}{CFAIL}{s}{ENDC}"
