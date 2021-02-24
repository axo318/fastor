from io import BytesIO
import time
import pycurl
import stem.control

# Static exit for us to make 2-hop circuits through. Picking ExitNinja, a
# particularly beefy one...
#
#   https://metrics.torproject.org/rs.html#details/379FB450010D17078B3766C2273303C358C3A442

EXIT_FINGERPRINT = '749EF4A434DFD00DAB31E93DE86233FB916D31E3'
# ENTRY_FINGERPRINT = '708A968F3644F8A547156368FEA3DB664110E631'

# TARGET = 'https://check.torproject.org/'
# TARGET = 'http://a5a7aram.ddns.net:8000/site.html'
TARGET = 'http://a5a7aram.ddns.net:8000/file.txt'

SOCKS_PORT = 9050
CONNECTION_TIMEOUT = 30  # timeout before we give up on a circuit


def query(url):
    """
    Uses pycurl to fetch a site using the proxy on the SOCKS_PORT.
    """

    output = BytesIO()

    query = pycurl.Curl()
    query.setopt(pycurl.URL, url)
    query.setopt(pycurl.PROXY, 'localhost')
    query.setopt(pycurl.PROXYPORT, SOCKS_PORT)
    query.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5_HOSTNAME)
    query.setopt(pycurl.CONNECTTIMEOUT, CONNECTION_TIMEOUT)
    query.setopt(pycurl.WRITEFUNCTION, output.write)

    try:
        query.perform()
        return output.getvalue()
    except pycurl.error as exc:
        raise ValueError("Unable to reach %s (%s)" % (url, exc))


def scan(controller, path):
    """
    Fetch check.torproject.org through the given path of relays, providing back
    the time it took.
    """

    circuit_id = controller.new_circuit(path, await_build=True)

    def attach_stream(stream):
        if stream.status == 'NEW':
            controller.attach_stream(stream.id, circuit_id)

    controller.add_event_listener(attach_stream, stem.control.EventType.STREAM)

    times = []

    try:
        controller.set_conf('__LeaveStreamsUnattached', '1')  # leave stream management to us

        for i in range(5):
            start_time = time.time()
            check_page = query(TARGET)
            time_taken = time.time() - start_time

            if 'van' not in check_page.decode("utf-8"):
                raise ValueError("Request didn't have the right content")

            times.append(time_taken)

        return times

    finally:
        controller.remove_event_listener(attach_stream)
        controller.reset_conf('__LeaveStreamsUnattached')


with stem.control.Controller.from_port() as controller:
    controller.authenticate()

    relay_fingerprints = [desc.fingerprint for desc in controller.get_network_statuses()]

    for fingerprint in relay_fingerprints:
        try:
            times_taken = scan(controller, [fingerprint, EXIT_FINGERPRINT])
            times_taken = ['%0.2f'%x for x in times_taken]
            print('%s => %s seconds' % (fingerprint, ' '.join(times_taken)))
        except Exception as exc:
            print('%s => %s' % (fingerprint, exc))
            # break
