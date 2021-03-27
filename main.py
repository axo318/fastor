import time

from fastor.client import getClient
from fastor.client.client import ClientException


def main():
    times = []
    client = getClient("vanilla")
    client.attach()

    for i in range(10):
        res = client.query("http://a5a7aram.ddns.net:8000/file.txt")
        times.append(res.time_lapsed)
        time.sleep(2)

    print(times)
    client.detach()
    print("goodbye")


if __name__ == "__main__":
    main()
