# FAQ and troubleshooting

## Every call fails with `AuthenticationError`

Print the errors Namecheap sent, they usually name the problem:

```python
from namecheap_sdk import AuthenticationError, Namecheap

try:
    with Namecheap() as nc:
        nc.balances()
except AuthenticationError as exc:
    print(exc.errors)
```

The usual causes, in order:

1. The IP address the request comes from is not on the whitelist, or `client_ip` does not match it. Check your public address with `curl https://api.ipify.org`.
2. The account has no API access, or does not meet Namecheap's requirements for the production API.
3. Sandbox credentials against production, or the other way round. The sandbox is a separate site with its own key.
4. A typo in the API user or key.

## `AuthenticationError: Missing credentials`

The client found no API user, key or client IP. All three are required. It looked at the arguments, the `NAMECHEAP_*` variables and the config files listed on [](settings.md#files).

## My change does not show up in `nslookup`

Resolvers cache answers for the record's TTL, so wait for the old TTL to pass. Also check that the domain uses Namecheap DNS: `nc.domains.get("example.com").dns_provider`, or `nc.dns.hosts("example.com").using_our_dns`.

## A record I did not touch disappeared

Some program wrote the zone at the same moment as yours, or `replace_all` was called with an incomplete list. The SDK only writes the full zone it just read plus your change, but two writers in parallel can overwrite each other. Keep DNS changes for one domain in one place. See [](dns.md#how-changes-are-saved).

## Why does every change make two requests?

Namecheap can only save a whole zone at once. The SDK reads it first so it can keep your other records. A change that would not alter anything makes only the read.

## How do I set the apex record?

Use `@`, or the domain itself: `nc.dns.point("example.com", "@", "203.0.113.10")`.

## How do I add a second `A` record next to the first?

```python
nc.dns.add("example.com", DNSRecord.a("www", "203.0.113.11"))
```

`add` keeps what is there. `point` and `replace` replace the whole set.

## `ValueError: TTL must be between 60 and 60000 seconds`

Namecheap only accepts TTLs in that range, and the SDK checks every record of the zone before it writes, not only the ones you change. If a record already in the zone has a TTL outside the range, every write to that domain stops with this error. Fix that record once, for example in the Namecheap dashboard, and writes work again.

## What are `URL`, `URL301` and `FRAME` records?

Namecheap's web redirects. See [](dns.md#redirect-records).

## How do I see what is sent?

Pass an `httpx.Client` with event hooks, see [](http-client.md#logging-every-request). Remember the API key is in the query string of `GET` requests.
