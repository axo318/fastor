from stem.control import Controller


def checkConnection(port=9051):
    """ Attempts to retrieve tor controller and authenticate to a running Tor instance  """
    with Controller.from_port(port=port) as controller:
        controller.authenticate()
