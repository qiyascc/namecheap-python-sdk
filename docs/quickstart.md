# Quickstart

This page builds one small script step by step: it lists the domains in your account, shows the records of one of them, and points a subdomain at a server. It assumes you have [installed the package](installation.md), turned on [API access](credentials.md) and whitelisted your IP.

## 1. Give the SDK your credentials

::::{tab-set}

:::{tab-item} Linux and macOS
```bash
export NAMECHEAP_API_USER=your-user
export NAMECHEAP_API_KEY=your-key
export NAMECHEAP_CLIENT_IP=203.0.113.5
```
:::

:::{tab-item} Windows (CMD)
```bat
set NAMECHEAP_API_USER=your-user
set NAMECHEAP_API_KEY=your-key
set NAMECHEAP_CLIENT_IP=203.0.113.5
```
:::
::::

With these set, `Namecheap()` needs no arguments. To practise on the sandbox, use your sandbox account and add `NAMECHEAP_ENVIRONMENT=sandbox`.

## 2. List your domains

Create `first.py`:

```python
from namecheap_sdk import Namecheap

with Namecheap() as nc:
    for domain in nc.domains.iter():
        print(domain.name, domain.expires, domain.auto_renew, domain.is_our_dns)
```

```bash
python first.py
```

```text
example.com 2027-03-14 True True
example.net 2026-12-02 False False
```

What happens here:

- `Namecheap()` reads the settings and checks that the user, key and client IP are all there. It does not send a request yet.
- `with` closes the connection pool when the block ends.
- `nc.domains.iter()` asks for one page of domains at a time and yields them one by one as {py:class}`~namecheap_sdk.Domain` objects.
- `is_our_dns` tells you whether the domain uses Namecheap's own DNS. Only those domains can be edited with `nc.dns`.

## 3. Read the zone

Add inside the `with` block:

```python
    hosts = nc.dns.hosts("example.com")
    print("Mail setting:", hosts.email_type)
    for record in hosts.records:
        print(record.type, record.name, record.data, record.ttl)
```

```text
Mail setting: MX
A @ 203.0.113.1 1800
CNAME www example.com. 1800
MX @ mail.example.com. 1800
```

`hosts()` returns the whole zone as a {py:class}`~namecheap_sdk.Hosts` object, including the domain's mail setting. When you only need the records, `nc.dns.list("example.com")` returns the list directly, and it can filter:

```python
nc.dns.list("example.com", "A")
nc.dns.list("example.com", "A", "www")
```

## 4. Point a subdomain at a server

```python
    nc.dns.point("example.com", "shop", "203.0.113.10", ttl=300)
    print(nc.dns.list("example.com", "A", "shop"))
```

```text
[DNSRecord(type='A', name='shop', data='203.0.113.10', ttl=300, priority=None, id=7, active=True)]
```

`point` picks `A` for an IPv4 address and `AAAA` for IPv6. Behind the scenes it reads the zone, replaces the `A` records of `shop`, keeps everything else exactly as it was, and writes the zone back. If `shop` already pointed at that address with that TTL, nothing is written at all. That makes the call safe to repeat.

DNS changes take a little while to reach resolvers. Check from your machine:

```bash
nslookup shop.example.com
```

## 5. Handle errors

```python
from namecheap_sdk import AuthenticationError, Namecheap, NamecheapError, NotFoundError

try:
    with Namecheap() as nc:
        nc.dns.point("example.com", "shop", "203.0.113.10")
except NotFoundError:
    print("example.com is not in this Namecheap account")
except AuthenticationError as exc:
    print("Check the API key and the IP whitelist:", exc)
except NamecheapError as exc:
    print("Namecheap said:", exc)
```

Every exception the SDK raises inherits from {py:class}`~namecheap_sdk.NamecheapError`. [](errors.md) lists them all.

## The same script, async

```python
import asyncio

from namecheap_sdk import AsyncNamecheap


async def main() -> None:
    async with AsyncNamecheap() as nc:
        async for domain in nc.domains.iter():
            print(domain.name)
        await nc.dns.point("example.com", "shop", "203.0.113.10")


asyncio.run(main())
```

## Where to go next

- [](configuration.md): all settings and the three ways to set them.
- [](dns.md): how changes are saved and every DNS method in detail.
- [](domains.md): availability, name servers and the registrar lock.
- [](examples/index.md): complete scripts for common jobs.
