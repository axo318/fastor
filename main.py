from fastor.client import getClient
from fastor.client.client import ClientException


def main():
    client = getClient("vanilla")

    attached = False
    while not attached:
        try:
            client.attach()
            attached = True
        except ClientException as e:
            print(e)

    res = None
    while True:
        try:
            res = client.query("http://a5a7aram.ddns.net:8000/file.txt")
        except ClientException as e:
            print(e)

        if res is not None:
            break
        else:
            client.re

    print(res)
    client.detach()
    print("goodbye")


if __name__ == "__main__":
    main()
