import stem.control

with stem.control.Controller.from_port() as controller:
        controller.authenticate()
        relay_fingerprints = [desc.fingerprint for desc in controller.get_network_statuses()]

print(len(relay_fingerprints))