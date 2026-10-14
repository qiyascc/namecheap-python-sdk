import sys

from namecheap_sdk import Namecheap, NotFoundError


def main() -> None:
    if len(sys.argv) != 4:
        print("usage: python subdomain.py <domain> <name> <ip>")
        sys.exit(1)

    domain, name, ip = sys.argv[1:]
    with Namecheap() as nc:
        try:
            current = nc.dns.list(domain, "A", name)
        except NotFoundError:
            print(f"{domain} is not in this Namecheap account")
            sys.exit(1)

        if [record.data for record in current] == [ip]:
            print(f"{name}.{domain} already points to {ip}")
            return

        nc.dns.point(domain, name, ip)
        print(f"{name}.{domain} now points to {ip}")


if __name__ == "__main__":
    main()
