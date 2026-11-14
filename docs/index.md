# Namecheap Python SDK

A small, typed Python client for the Namecheap Domains and DNS API. It works in sync and async code, turns Namecheap's XML into plain dataclasses, and makes the "replace everything" DNS API safe to use one record at a time.

```python
from namecheap_sdk import Namecheap

with Namecheap("api_user", "API_KEY", client_ip="203.0.113.5") as nc:
    nc.dns.point("example.com", "shop", "203.0.113.10")
```

That call makes `shop.example.com` resolve to `203.0.113.10` and leaves every other record of the domain as it was.

The package is on PyPI as `namecheap-python-sdk` and is imported as `namecheap_sdk`, so it does not clash with older `namecheap` packages. It needs Python 3.10 or newer.

## Where to start

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} Installation
:link: installation
:link-type: doc

Set up a virtual environment, install the package with pip, uv or Poetry, and check that it imports.
:::

:::{grid-item-card} API access
:link: credentials
:link-type: doc

Turn on API access, whitelist your IP and try everything in the sandbox first.
:::

:::{grid-item-card} Quickstart
:link: quickstart
:link-type: doc

Write your first script: list your domains, read a zone and point a subdomain at a server.
:::

:::{grid-item-card} Configuration
:link: configuration
:link-type: doc

Pass settings in code, through `NAMECHEAP_*` environment variables or from a TOML, YAML or JSON file.
:::

:::{grid-item-card} DNS records
:link: dns
:link-type: doc

How changes are saved, every record method, redirect records and the shortcuts.
:::

:::{grid-item-card} Domains
:link: domains
:link-type: doc

Your portfolio, availability and premium prices, name servers, registrar lock and account balance.
:::

:::{grid-item-card} Recipes
:link: examples/index
:link-type: doc

Complete scripts: a subdomain per customer, dynamic DNS, Let's Encrypt DNS-01, Django and FastAPI.
:::

:::{grid-item-card} API reference
:link: api
:link-type: doc

Every public class, method and exception with its signature.
:::
::::

## What the SDK covers

- DNS: read the zone, list and check records, add, replace, rewrite the whole zone and delete, plus Namecheap's own URL redirect and frame records.
- DNS shortcuts: `point`, `unpoint`, `alias` and `set_txt`.
- Safe writes: Namecheap's `setHosts` replaces the whole zone, so the SDK always reads the zone, applies your change and writes the full list back. If nothing changes, nothing is written.
- Domains: list and iterate over your portfolio, read one domain, check availability and premium prices, list TLDs, read and set name servers, read and set the registrar lock.
- Account: read your balances.
- Typed errors mapped from Namecheap's error numbers, even though Namecheap answers HTTP 200 for most failures.
- Automatic retries for rate limits, server errors and dropped connections.
- Settings through [goodconf](https://github.com/lincolnloop/goodconf): code, environment variables or a config file.
- Every message the SDK prints lives in a YAML file you can translate.

It has three siblings with the same shape: the [GoDaddy](https://godaddy-python-sdk.readthedocs.io/en/latest/), [Hostinger](https://hostinger-python-sdk.readthedocs.io/en/latest/) and [DigitalOcean](https://digitalocean-python-sdk.readthedocs.io/en/latest/) SDKs. `dns.point("example.com", "shop", ip)` does the same thing in all four.

```{toctree}
:hidden:
:caption: Getting started

installation
credentials
quickstart
configuration
```

```{toctree}
:hidden:
:caption: Guides

dns
domains
account
async
errors
retries-timeouts
http-client
messages
testing
```

```{toctree}
:hidden:
:caption: Examples

examples/index
examples/customer-subdomains
examples/dynamic-dns
examples/acme-dns-01
examples/migrate-between-providers
examples/web-frameworks
examples/scheduled-jobs
```

```{toctree}
:hidden:
:caption: Reference

api
settings
faq
changelog
```

```{toctree}
:hidden:
:caption: Project

development
about
```
