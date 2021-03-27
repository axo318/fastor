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

    worked = False
    res = None
    while not worked:
        try:
            res = client.query("http://a5a7aram.ddns.net:8000/file.txt")
            worked = True
        except ClientException as e:
            print(e)

    print(res)
    client.detach()
    print("goodbye")


if __name__ == "__main__":
    main()
