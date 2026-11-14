# Domains

`nc.domains` covers the domains in your account: listing them, reading their details, checking availability, name servers and the registrar lock.

## Listing your domains

### `iter`

```python
for domain in nc.domains.iter():
    print(domain.name, domain.expires, domain.auto_renew)
```

Yields every domain as a {py:class}`~namecheap_sdk.Domain`, one page at a time behind the scenes. Pages hold `page_size` domains (default 100, the most Namecheap allows). It stops after the last page, using the total Namecheap reports.

### `list`

```python
nc.domains.list()
nc.domains.list(list_type="EXPIRING", sort_by="EXPIREDATE")
nc.domains.list(search="shop")
```

Fetches **all** pages and returns one `list[Domain]`. Use it when you want the whole list at once, and `iter` when the portfolio is large and you can process domains as they arrive.

Both take the same keyword arguments:

| Argument | Sent as | Meaning |
| --- | --- | --- |
| `list_type` | `ListType` | `ALL` (default), or another list type Namecheap supports, such as `EXPIRING` or `EXPIRED`. Upper cased for you. |
| `search` | `SearchTerm` | Only domains whose name contains this text. |
| `sort_by` | `SortBy` | Sort order, for example `NAME`, `EXPIREDATE` or `CREATEDATE`. Upper cased for you. |

### The Domain dataclass

| Field | Type | Meaning |
| --- | --- | --- |
| `name` | `str` | The domain. |
| `id` | `int` or `None` | Namecheap's id. |
| `user` | `str` | The account it belongs to. |
| `created` | `date` or `None` | Registration date. |
| `expires` | `date` or `None` | Expiry date. |
| `is_expired` | `bool` | |
| `is_locked` | `bool` | Registrar lock is on. |
| `auto_renew` | `bool` | |
| `whois_guard` | `str` | Privacy status as Namecheap reports it, for example `ENABLED`. |
| `is_premium` | `bool` | |
| `is_our_dns` | `bool` | The domain uses Namecheap's DNS, so `nc.dns` can edit it. |

Namecheap sends dates as `MM/DD/YYYY`. The SDK turns them into `datetime.date` objects.

## One domain

```python
info = nc.domains.get("example.com")
print(info.status, info.expires, info.whois_guard, info.dns_provider)
```

Returns a {py:class}`~namecheap_sdk.DomainInfo`:

| Field | Meaning |
| --- | --- |
| `name` | The domain. |
| `id` | Namecheap's id. |
| `status` | Status text as Namecheap reports it. |
| `owner` | Owner account name. |
| `is_owner` | `True` if the API user owns it. |
| `is_premium` | |
| `created`, `expires` | `date` objects. |
| `whois_guard` | `True` if privacy protection is on. |
| `dns_provider` | The DNS type Namecheap reports for the domain (`ProviderType`). |

A domain that is not in your account raises `NotFoundError`.

## Availability

### One name

```python
check = nc.domains.available("my-new-idea.com")
if check.available:
    if check.premium:
        print("Premium name:", check.registration_price, "to register,", check.renewal_price, "to renew")
    else:
        print("Free to register at the normal price")
```

Returns an {py:class}`~namecheap_sdk.Availability`:

| Field | Meaning |
| --- | --- |
| `domain` | The name checked. |
| `available` | `True` if it can be registered. |
| `premium` | `True` for premium names with their own price. |
| `registration_price`, `renewal_price`, `restore_price`, `transfer_price` | `Decimal` prices, only filled for premium names. |
| `icann_fee`, `eap_fee` | `Decimal` fees when Namecheap reports them. |
| `description` | Extra text from Namecheap, if any. |

The SDK fills the price fields only for premium names. For a normal name they stay `None`, and the price is the regular one for that TLD in your account.

### Many names

```python
for row in nc.domains.available_many(["one.com", "two.net", "three.org"]):
    print(row.domain, row.available)
```

One request for the whole list. An empty list raises `ValueError`.

## TLDs

```python
for tld in nc.domains.tlds():
    print(tld.name, tld.min_years, tld.max_years, tld.api_registerable)
```

Each {py:class}`~namecheap_sdk.Tld` has `name`, `description`, `type`, `min_years`, `max_years`, `api_registerable`, `api_renewable`, `api_transferable` and `supports_idn`.

## Name servers

### Reading

```python
ns = nc.domains.nameservers("example.com")
print(ns.servers, ns.using_our_dns)
```

Returns a {py:class}`~namecheap_sdk.Nameservers` with the list of `servers` and `using_our_dns`.

### Using your own

```python
nc.domains.set_nameservers("example.com", ["ns1.example.net", "ns2.example.net"])
```

Points the domain at other name servers, for example Cloudflare or DigitalOcean. You need at least two, otherwise `ValueError`. Trailing dots and blank entries are removed. Returns `True` when Namecheap confirms the change.

```{warning}
After this, `nc.dns` cannot edit the domain any more: the records live with the new DNS provider.
```

### Going back to Namecheap DNS

```python
nc.domains.use_default_nameservers("example.com")
```

Switches the domain back to Namecheap BasicDNS, which the DNS methods need. Returns `True` when confirmed.

## Registrar lock

The registrar lock stops the domain from being transferred away.

```python
nc.domains.is_locked("example.com")   # True or False
nc.domains.lock("example.com")
nc.domains.unlock("example.com")
```

`lock` and `unlock` return `True` when Namecheap confirms. Unlock only right before you start a transfer.

## A worked example: expiry report

```python
from datetime import date, timedelta

from namecheap_sdk import Namecheap

soon = date.today() + timedelta(days=60)

with Namecheap() as nc:
    for domain in nc.domains.iter():
        if domain.expires and domain.expires <= soon and not domain.auto_renew:
            print(f"{domain.name} expires on {domain.expires} and will not renew")
```

Run it weekly with [](examples/scheduled-jobs.md).
