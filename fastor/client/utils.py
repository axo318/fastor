from collections import defaultdict
from typing import Dict


def parametrized(dec):
    """ Deep decorator for enabling other decorators to accept arguments """
    def layer(*args, **kwargs):
        def repl(f):
            return dec(f, *args, **kwargs)
        return repl
    return layer


class ClientType:
    """ Static class with a decorator for registering client types upon runtime """
    d: Dict[str, type] = defaultdict()

    @staticmethod
    @parametrized
    def register(subclass, client_type: str):
        ClientType.d[client_type] = subclass
        return subclass
