import stem

from fastor.common import FastorObject


SOCKS_PORT = 9050
CONTROL_PORT = 9051
CONNECTION_TIMEOUT = 15  # timeout before we give up on a circuit


class TorHandler(FastorObject):
    def __init__(self):
        """ Interface to stem.Controller  """
        self.tor_controller = None

    # Tor controller
    def _initTorController(self):
        try:
            self.tor_controller = stem.control.Controller.from_port(port=CONTROL_PORT)
        except stem.SocketError as exc:
            self.error(f"Unable to connect to tor on port {CONTROL_PORT}: {exc}")
            return False
        try:
            self.tor_controller.authenticate()
        except stem.connection.AuthenticationFailure as exc:
            self.error(f"Unable to authenticate: {exc}")
            return False
        self.info(f"Tor is running version {self.tor_controller.get_version()}")
        return True
