import unittest

from fastor.torHandler import TorHandler


SOCKS_PORT = 9050
CONTROL_PORT = 9051
CONNECTION_TIMEOUT = 15  # timeout before we give up on a circuit


class TorHandlerTestCase(unittest.TestCase):

    def test_attach_detach(self):
        # Initialize and attach to Tor
        tor_handler = TorHandler(SOCKS_PORT, CONTROL_PORT, CONNECTION_TIMEOUT)
        tor_handler.attach()

        # Get consensus
        consensus = tor_handler.getDescriptors()

        # Build random circuit using 2 fingerprints from consensus
        fps = [desc.fingerprint for desc in consensus]

        # Good
        c_id = tor_handler.createCircuit([fps[0], "2D13F31E8BD2D13B9A1F7E0351FB55ADD142FEED"], await_build=True)
        # Bad
        # c_id = tor_handler.createCircuit([fps[0], fps[1]], await_build=True)

        # Query through the new circuit
        query_result = tor_handler.performQuery("http://a5a7aram.ddns.net:8000/file.txt", c_id)
        print(query_result)

        # Close circuit
        tor_handler.closeCircuit(c_id)

        # Detach TorHandler
        tor_handler.detach()


if __name__ == '__main__':
    unittest.main()
