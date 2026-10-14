# namecheap-python-sdk

A small, typed Python client for the Namecheap Domains and DNS API. It works with both sync and async code, turns Namecheap's XML into plain dataclasses, and makes the "replace everything" DNS API safe to use one record at a time.

```python
from namecheap_sdk import Namecheap

with Namecheap("api_user", "API_KEY", client_ip="203.0.113.5") as nc:
    nc.dns.point("example.com", "shop", "203.0.113.10")
```

That call makes `shop.example.com` resolve to `203.0.113.10` and leaves every other record of the domain as it was.

## Install

```bash
pip install git+https://github.com/qiyascc/namecheap-python-sdk.git
```

Requires Python 3.10 or newer. Dependencies: [httpx](https://www.python-httpx.org/), [goodconf](https://github.com/lincolnloop/goodconf), pydantic and PyYAML. XML is parsed with the standard library.

The import name is `namecheap_sdk`, so it does not clash with older `namecheap` packages.

## Before you start

1. Enable API access under Profile, Tools, Business & Dev Tools, Namecheap API Access. Namecheap only opens the production API to accounts that meet its requirements, so check that page if every call fails.
2. Whitelist the IPv4 address of the machine that makes the calls on the same page. Every request carries that address as `ClientIp`, and calls from any other address are rejected with `AuthenticationError`.
3. Try things in the sandbox first. It is a separate site, [sandbox.namecheap.com](https://www.sandbox.namecheap.com), with its own account, key and whitelist.

## Configuration

Settings are loaded with [goodconf](https://github.com/lincolnloop/goodconf), so you can configure the client from code, from environment variables or from a config file. Values passed in code win over the environment, and the environment wins over the file.

```python
nc = Namecheap("api_user", "API_KEY", client_ip="203.0.113.5")
nc = Namecheap("api_user", "API_KEY", client_ip="203.0.113.5", environment="sandbox")
```

```bash
export NAMECHEAP_API_USER=api_user
export NAMECHEAP_API_KEY=...
export NAMECHEAP_CLIENT_IP=203.0.113.5
```

```toml
api_user = "api_user"
api_key = "..."
client_ip = "203.0.113.5"
environment = "production"
```

With no arguments, the client looks for `namecheap.toml`, `namecheap.yaml`, `namecheap.yml` or `namecheap.json` in the working directory. To load a file from somewhere else, set `NAMECHEAP_CONFIG=/path/to/file`, or pass `config_file=` to the client. YAML files need the `yaml` extra, and TOML files on Python 3.10 need the `toml` extra:

```bash
pip install "namecheap-python-sdk[yaml] @ git+https://github.com/qiyascc/namecheap-python-sdk.git"
```

| Setting | Env variable | Default |
| --- | --- | --- |
| `api_user` | `NAMECHEAP_API_USER` | |
| `api_key` | `NAMECHEAP_API_KEY` | |
| `username` | `NAMECHEAP_USERNAME` | same as `api_user` |
| `client_ip` | `NAMECHEAP_CLIENT_IP` | |
| `environment` | `NAMECHEAP_ENVIRONMENT` | `production` |
| `base_url` | `NAMECHEAP_BASE_URL` | taken from `environment` |
| `production_url` | `NAMECHEAP_PRODUCTION_URL` | `https://api.namecheap.com/xml.response` |
| `sandbox_url` | `NAMECHEAP_SANDBOX_URL` | `https://api.sandbox.namecheap.com/xml.response` |
| `commands.*` | `NAMECHEAP_COMMANDS__<NAME>` | see below |
| `timeout` | `NAMECHEAP_TIMEOUT` | `30` |
| `max_retries` | `NAMECHEAP_MAX_RETRIES` | `3` |
| `max_retry_wait` | `NAMECHEAP_MAX_RETRY_WAIT` | `60` |
| `backoff_base` | `NAMECHEAP_BACKOFF_BASE` | `1` |
| `backoff_cap` | `NAMECHEAP_BACKOFF_CAP` | `16` |
| `page_size` | `NAMECHEAP_PAGE_SIZE` | `100` (the API allows 10 to 100) |
| `default_ttl` | `NAMECHEAP_DEFAULT_TTL` | `1800` |
| `user_agent` | `NAMECHEAP_USER_AGENT` | `namecheap-python-sdk/{version}` |

`username` is the account the commands run on. It only differs from `api_user` when a reseller acts for a customer.

### Commands

Namecheap has one URL and picks the action from a `Command` parameter. The command names are part of the settings, so nothing is pinned in the code:

| Name | Default |
| --- | --- |
| `get_hosts` | `namecheap.domains.dns.getHosts` |
| `set_hosts` | `namecheap.domains.dns.setHosts` |
| `get_nameservers` | `namecheap.domains.dns.getList` |
| `set_custom_nameservers` | `namecheap.domains.dns.setCustom` |
| `set_default_nameservers` | `namecheap.domains.dns.setDefault` |
| `list_domains` | `namecheap.domains.getList` |
| `domain_info` | `namecheap.domains.getInfo` |
| `check` | `namecheap.domains.check` |
| `tlds` | `namecheap.domains.getTldList` |
| `get_lock` | `namecheap.domains.getRegistrarLock` |
| `set_lock` | `namecheap.domains.setRegistrarLock` |
| `balances` | `namecheap.users.getBalances` |

## DNS

These methods work while the domain uses Namecheap's own name servers (BasicDNS or PremiumDNS). Record names are relative to the domain and the apex is `@`. You can also pass a full name like `www.example.com`, it is turned into `www` for you.

```python
from namecheap_sdk import Namecheap, DNSRecord

nc = Namecheap()

nc.dns.list("example.com")
nc.dns.list("example.com", "A")
nc.dns.list("example.com", "A", "www")
nc.dns.exists("example.com", "A", "shop")

hosts = nc.dns.hosts("example.com")
hosts.records, hosts.email_type, hosts.using_our_dns
```

Each record is a `DNSRecord`:

```python
DNSRecord(type='A', name='www', data='203.0.113.10', ttl=1800, priority=None, id=12, active=True)
```

### How changes are saved

Namecheap's `setHosts` replaces the whole zone: any record left out of the call is deleted. So every change here reads the current records first, applies your change, and writes the full list back. If nothing actually changes, nothing is written. The mail setting (`EmailType`) is kept as it was, set to `MX` when the zone has MX records, or set to whatever you pass as `email_type=`.

Two programs editing the same domain at the same moment can still overwrite each other, because the API has no locking. Keep DNS changes for one domain in one place.

### Creating and changing records

```python
nc.dns.add(
    "example.com",
    DNSRecord.a("api", "203.0.113.20"),
    DNSRecord.txt("@", "google-site-verification=abc"),
    DNSRecord.mx("@", "mail.example.com", priority=10),
    DNSRecord.caa("@", "letsencrypt.org"),
)

nc.dns.replace("example.com", "A", "www", ["203.0.113.10", "203.0.113.11"], ttl=600)

nc.dns.delete("example.com", "A", "old")
nc.dns.delete("example.com", "A", "www", data="203.0.113.11")

nc.dns.replace_all("example.com", [DNSRecord.a("@", "203.0.113.10"), DNSRecord.cname("www", "example.com")])
```

`add` keeps everything and adds records that are not there yet. `replace` swaps every record with that type and name and keeps them in the same place in the zone. `delete` returns how many records it removed. `replace_all` writes exactly the list you pass.

Namecheap also has its own redirect records, which other providers do not:

```python
nc.dns.add("example.com", DNSRecord.url("old", "https://example.com/new"))
nc.dns.add("example.com", DNSRecord.url("tmp", "https://example.com", permanent=False))
nc.dns.add("example.com", DNSRecord.frame("promo", "https://landing.example.net"))
```

TTL must be between 60 and 60000 seconds. Host names in `CNAME`, `ALIAS`, `NS` and `MX` records get their trailing dot, and `DNSRecord.caa("@", "letsencrypt.org")` becomes `0 issue "letsencrypt.org"`.

### Shortcuts

```python
nc.dns.point("example.com", "shop", "203.0.113.10")
nc.dns.point("example.com", "shop", "2001:db8::10")
nc.dns.alias("example.com", "docs", "example.github.io")
nc.dns.set_txt("example.com", "_acme-challenge", "token-value", ttl=60)
nc.dns.unpoint("example.com", "shop")
```

`point` picks `A` or `AAAA` from the address you pass.

### Example: one subdomain per customer

```python
from namecheap_sdk import Namecheap

SERVER_IP = "203.0.113.10"

def create_customer_site(slug: str) -> str:
    with Namecheap() as nc:
        if nc.dns.exists("example.com", "A", slug):
            raise ValueError(f"{slug}.example.com is already taken")
        nc.dns.point("example.com", slug, SERVER_IP, ttl=300)
    return f"{slug}.example.com"
```

## Domains

```python
for domain in nc.domains.iter():
    print(domain.name, domain.expires, domain.auto_renew)

nc.domains.list(list_type="EXPIRING", sort_by="EXPIREDATE")
nc.domains.list(search="shop")

info = nc.domains.get("example.com")
info.status, info.expires, info.whois_guard

check = nc.domains.available("my-new-idea.com")
if check.available and check.premium:
    print(check.registration_price)

nc.domains.available_many(["one.com", "two.net"])
nc.domains.tlds()

nc.domains.nameservers("example.com").servers
nc.domains.set_nameservers("example.com", ["ns1.example.net", "ns2.example.net"])
nc.domains.use_default_nameservers("example.com")

nc.domains.is_locked("example.com")
nc.domains.lock("example.com")
nc.domains.unlock("example.com")

nc.balances()
```

`use_default_nameservers` switches the domain back to Namecheap BasicDNS, which the DNS methods need.

## Async

`AsyncNamecheap` has the same methods. Await them.

```python
import asyncio
from namecheap_sdk import AsyncNamecheap

async def main():
    async with AsyncNamecheap() as nc:
        records = await nc.dns.list("example.com", "A")
        await nc.dns.point("example.com", "shop", "203.0.113.10")
        async for domain in nc.domains.iter():
            print(domain.name)

asyncio.run(main())
```

## Errors

Namecheap answers HTTP 200 even when a call fails and puts the error in the XML. The client turns those answers into exceptions. All of them inherit from `NamecheapError`.

| Exception | When |
| --- | --- |
| `AuthenticationError` | wrong user or key, missing credentials, or a `ClientIp` that is not whitelisted |
| `NotFoundError` | the domain is not found or not in this account (2019166, 2016166) |
| `PermissionDeniedError` | the domain cannot be edited through the API (2030166) |
| `ValidationError` | a parameter was rejected, for example too many records |
| `RateLimitError` | Namecheap says there are too many requests |
| `ServerError` | 5xx answers and errors from Namecheap's upstream registry |
| `APIError` | any other error in the XML |
| `APIConnectionError` / `APITimeoutError` | the request never got an answer |

Errors carry Namecheap's error `number`, the full `errors` list, the `command` that failed and the raw `response`.

```python
from namecheap_sdk import NotFoundError

try:
    nc.dns.list("not-mine.com")
except NotFoundError as exc:
    print(exc.number, exc.message)
```

## Retries and timeouts

Namecheap does not publish its limits in the API docs, and its support has quoted around 20 calls per minute, 700 per hour and 8,000 per day for a key. Too many calls come back as an error, which the client waits on and retries with exponential backoff, together with server errors and dropped connections. Every command this SDK sends can be repeated safely, because `setHosts` writes the full list each time.

```python
nc = Namecheap(timeout=10, max_retries=5)
```

Set `max_retries=0` to turn retries off. To use proxies or a custom transport, pass your own `httpx.Client` or `httpx.AsyncClient` as `http_client=`.

## Messages

Every error and validation message the SDK produces is stored in `namecheap_sdk/messages.yaml`, so none of them are hardcoded. You can replace some or all of them, for example to translate them:

```yaml
value:
  empty_name: Record adı boş ola bilməz
error:
  timeout: "Sorğu vaxtı bitdi: {error}"
```

```python
from namecheap_sdk import messages

messages.use("messages.az.yaml")
messages.use({"value.empty_name": "Record adı boş ola bilməz"})
```

Unknown keys raise `KeyError`, which catches typos early. Call `messages.reset()` to go back to the defaults.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```

The tests use `httpx.MockTransport`, so they never touch the real API.

## License

MIT
