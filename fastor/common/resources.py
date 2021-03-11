
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
