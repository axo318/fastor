from fastor.client import getClient


def main():
    client = getClient("vanilla")
    client.attach()
    res = client.query("http://facebook.com")

    print(res)

    client.detach()


if __name__ == "__main__":
    main()