# DNS records

Everything under `nc.dns` edits the host records of a domain. These methods only work while the domain uses Namecheap's own name servers (BasicDNS or PremiumDNS). If it points elsewhere, `nc.domains.use_default_nameservers(domain)` switches it back, see [](domains.md#name-servers).

## How changes are saved

This is the one thing to understand before using the DNS methods.

Namecheap's API has no call to add, change or delete one record. It has `getHosts`, which returns the whole zone, and `setHosts`, which **replaces** the whole zone: any record you leave out of a `setHosts` call is deleted.

So every write in this SDK does three steps:

1. Read the current records with `getHosts`.
2. Apply your change to that list in Python.
3. Write the full list back with `setHosts`, but only if something actually changed.

You call `nc.dns.point(...)` and the other records of the domain stay exactly as they were.

```{warning}
The API has no locking. If two programs change the same domain at the same moment, both read the old zone, and the one that writes last wins: the other change is lost. Keep DNS changes for one domain in one place, for example a single worker, and do not run writes to the same domain in parallel.
```

### The mail setting

A Namecheap zone also has a mail setting, `EmailType`, which says how the domain's mail is handled. The SDK reads it with the zone and sends it back with every write:

- If you pass `email_type=` (to `add` or `replace_all`), that value is sent.
- Otherwise, if the new zone has `MXE` records, it is `MXE`, and if it has `MX` records, it is `MX`.
- Otherwise the current setting is kept, unless it was `MX`, `MXE` or `NONE` and the zone no longer has mail records, in which case it is left out.

In practice: add `MX` records and the mail setting follows. Use `email_type=` only when you know you need a specific Namecheap mail mode.

## Names, types and the apex

Record names are relative to the domain, and the apex is `@`. You can also pass a full name: `www.example.com` and `www.example.com.` both become `www` when the domain is `example.com`.

| You want | Pass as `name` |
| --- | --- |
| `example.com` itself | `@` or `example.com` |
| `www.example.com` | `www` or `www.example.com` |
| `_acme-challenge.example.com` | `_acme-challenge` |

A name with a trailing dot that is not inside the domain, like `www.other.org.`, raises `ValueError`. Names are lower cased.

Types are strings (`"A"`, `"txt"`) or members of {py:class}`~namecheap_sdk.RecordType`: `A`, `AAAA`, `ALIAS`, `CAA`, `CNAME`, `MX`, `MXE`, `NS`, `TXT`, `URL`, `URL301` and `FRAME`.

The domain must be a full name with a TLD, like `example.com` or `example.co.uk`. Namecheap wants it split into the part before the first dot and the rest, and the SDK does that for you.

## The DNSRecord dataclass

```python
DNSRecord(type='A', name='www', data='203.0.113.10', ttl=1800, priority=None, id=12, active=True)
```

| Field | Meaning |
| --- | --- |
| `type` | Record type, upper case. |
| `name` | Relative name, `@` for the apex. |
| `data` | The value: address, host name or text. Namecheap calls it `Address`. |
| `ttl` | Seconds. `None` on a new record means "use `default_ttl`", or keep the old TTL when replacing. |
| `priority` | `MX` and `MXE` only. Namecheap calls it `MXPref`. Defaults to 10 when writing. |
| `id` | Namecheap's `HostId`. Read only, ignored when comparing records. |
| `active` | Namecheap's `IsActive`. Read only, ignored when comparing records. |

`record.fqdn("example.com")` gives the full name, for example `www.example.com`.

### Constructors

```python
from namecheap_sdk import DNSRecord

DNSRecord.a("www", "203.0.113.10")
DNSRecord.aaaa("www", "2001:db8::10")
DNSRecord.cname("blog", "example.github.io")
DNSRecord.alias("@", "lb.example.net")
DNSRecord.txt("@", "v=spf1 include:spf.example.net ~all")
DNSRecord.mx("@", "mail.example.com", priority=10)
DNSRecord.ns("eu", "ns1.example.net")
DNSRecord.caa("@", "letsencrypt.org")
DNSRecord.url("old", "https://example.com/new")
DNSRecord.url("tmp", "https://example.com", permanent=False)
DNSRecord.frame("promo", "https://landing.example.net")
```

| Constructor | Result |
| --- | --- |
| `a(name, ip, ttl=None)` | `A`. Raises `ValueError` for anything but an IPv4 address. |
| `aaaa(name, ip, ttl=None)` | `AAAA`. Raises `ValueError` for anything but an IPv6 address. |
| `cname(name, target, ttl=None)` | `CNAME`. The target gets a trailing dot. |
| `alias(name, target, ttl=None)` | `ALIAS`, Namecheap's CNAME-like record that also works at the apex. |
| `txt(name, value, ttl=None)` | `TXT`. |
| `mx(name, host, priority=10, ttl=None)` | `MX`. The host gets a trailing dot. |
| `ns(name, host, ttl=None)` | `NS`, to delegate a subdomain. |
| `caa(name, value, tag="issue", flags=0, ttl=None)` | `CAA`. `caa("@", "letsencrypt.org")` becomes `0 issue "letsencrypt.org"`. |
| `url(name, target, permanent=True, ttl=None)` | Namecheap redirect: `URL301` (permanent) or `URL` (temporary). |
| `frame(name, target, ttl=None)` | Namecheap masked redirect: shows the target inside a frame. |

Host names in `CNAME`, `ALIAS`, `NS` and `MX` records always get their trailing dot, whether you build the record with a constructor or by hand.

## Reading

### `hosts`

```python
hosts = nc.dns.hosts("example.com")
hosts.records          # list[DNSRecord]
hosts.email_type       # "MX", "MXE", "FWD", ... or None
hosts.using_our_dns    # True when the domain uses Namecheap DNS
hosts.domain
```

Returns the whole zone as a {py:class}`~namecheap_sdk.Hosts` object, with the mail setting.

### `list`

```python
nc.dns.list("example.com")
nc.dns.list("example.com", "A")
nc.dns.list("example.com", "A", "www")
nc.dns.list("example.com", name="www")
```

Returns `list[DNSRecord]`. The filtering happens in Python after one `getHosts` call, since Namecheap has no filtered read.

### `exists`

```python
nc.dns.exists("example.com", "A", "shop")
```

`True` when the zone has at least one record of that type and name.

## Writing

All writes go through the read, change, write cycle described above. None of them send a request if the zone would come out unchanged.

### `add`

```python
nc.dns.add(
    "example.com",
    DNSRecord.a("api", "203.0.113.20"),
    DNSRecord.txt("@", "google-site-verification=abc"),
    DNSRecord.mx("@", "mail.example.com", priority=10),
    DNSRecord.caa("@", "letsencrypt.org"),
)
```

Keeps every existing record and appends the new ones. A record that is already there (same type, name and value) is skipped, so running the same `add` twice does not create duplicates. Returns the list of records that were actually added. Pass `email_type=` to set the mail mode at the same time.

### `replace`

```python
nc.dns.replace("example.com", "A", "www", ["203.0.113.10", "203.0.113.11"], ttl=600)
nc.dns.replace("example.com", "TXT", "@", "v=spf1 -all")
nc.dns.replace("example.com", "MX", "@", [
    DNSRecord.mx("@", "mx1.example.net", priority=10),
    DNSRecord.mx("@", "mx2.example.net", priority=20),
])
```

After the call, that type and name hold exactly the values you passed. The new records take the place of the old ones in the zone, so the order of the other records does not change. `values` is a string, a list of strings, a `DNSRecord` or a list of them. Returns the records that were written.

When you pass no `ttl` and a value already existed, it keeps its old TTL and priority. New values get `default_ttl`.

### `replace_all`

```python
nc.dns.replace_all("example.com", [
    DNSRecord.a("@", "203.0.113.10"),
    DNSRecord.cname("www", "example.com"),
    DNSRecord.mx("@", "mail.example.com"),
])
```

```{danger}
`replace_all` writes exactly the list you pass. Every record not in it is deleted, including mail and verification records. Read the zone first, change the list, then write it back.
```

### `delete`

```python
removed = nc.dns.delete("example.com", "A", "old")
removed = nc.dns.delete("example.com", "A", "www", data="203.0.113.11")
```

Without `data`, deletes every record of that type and name. With `data`, deletes only the record holding that value and keeps the others. Returns the number of records removed, `0` if there was nothing to delete. It never raises because a record is missing.

For host types (`CNAME`, `ALIAS`, `NS`, `MX`), `data` is compared without the trailing dot and without regard to case, so `mail.example.com` matches `Mail.Example.com.`.

## Shortcuts

```python
nc.dns.point("example.com", "shop", "203.0.113.10")
nc.dns.point("example.com", "shop", "2001:db8::10")
nc.dns.alias("example.com", "docs", "example.github.io")
nc.dns.set_txt("example.com", "_acme-challenge", "token-value", ttl=60)
nc.dns.unpoint("example.com", "shop")
```

| Method | What it does |
| --- | --- |
| `point(domain, name, ip, ttl=None)` | `A` or `AAAA` record with that address, replacing the old set. |
| `unpoint(domain, name, ip_version=4)` | Deletes the `A` (or `AAAA` with `ip_version=6`) records. Returns how many. |
| `alias(domain, name, target, ttl=None)` | Sets a `CNAME`. |
| `set_txt(domain, name, values, ttl=None)` | Sets the `TXT` values of a name, one string or a list. |

## Redirect records

Namecheap offers web redirects as DNS records, which other providers do not:

```python
nc.dns.add("example.com", DNSRecord.url("old", "https://example.com/new"))
nc.dns.add("example.com", DNSRecord.url("tmp", "https://example.com", permanent=False))
nc.dns.add("example.com", DNSRecord.frame("promo", "https://landing.example.net"))
```

`URL301` sends a permanent redirect, `URL` a temporary one, and `FRAME` shows the target page inside a frame under your own address.

## TTL rules

Namecheap accepts TTLs from 60 to 60000 seconds. The SDK checks every TTL before the zone is written and raises `ValueError` if one is out of range, so a typo cannot reach Namecheap.

## A worked example: moving a site

```python
from namecheap_sdk import Namecheap

OLD, NEW = "203.0.113.10", "198.51.100.7"

with Namecheap() as nc:
    names = sorted({r.name for r in nc.dns.list("example.com", "A") if r.data == OLD})
    for name in names:
        nc.dns.replace("example.com", "A", name, NEW)
```

Each `replace` is one read and one write. For a large zone it is quicker to read once, edit, and write once with `replace_all`:

```python
from dataclasses import replace

with Namecheap() as nc:
    hosts = nc.dns.hosts("example.com")
    records = [replace(r, data=NEW) if r.type == "A" and r.data == OLD else r for r in hosts.records]
    nc.dns.replace_all("example.com", records)
```

`replace_all` keeps the current mail setting unless you pass `email_type=`.

## Async

`AsyncNamecheap().dns` has the same methods with the same arguments. Await them, and remember the warning above: do not run writes to the same domain in parallel.

```python
async with AsyncNamecheap() as nc:
    await nc.dns.point("example.com", "shop", "203.0.113.10")
```
