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
            res = client.query("http://facebook.com")
            worked = True
        except ClientException as e:
            print(e)

    print(res)
    client.detach()
    print("goodbye")


if __name__ == "__main__":
    main()
