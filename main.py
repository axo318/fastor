from fastor.client import getClient
from fastor.client.client import ClientException


def main():
    client = getClient("vanilla")

    client.attach()

    res = client.query("http://a5a7aram.ddns.net:8000/file.txt")

    print(res)
    client.detach()
    print("goodbye")


if __name__ == "__main__":
    main()
