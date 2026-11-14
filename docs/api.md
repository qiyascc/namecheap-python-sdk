# API reference

This page lists every public class and function with its signature. The guides explain how to use them: [](dns.md), [](domains.md), [](account.md), [](errors.md) and [](configuration.md).

Everything below can be imported from `namecheap_sdk`, except the resource classes, which you reach through a client (`nc.dns`, `nc.domains`).

## Clients

`Namecheap` is the sync client and `AsyncNamecheap` the async one. Both take the same arguments:

| Argument | Meaning |
| --- | --- |
| `api_user`, `api_key` | Your API user and key. Positional. |
| `client_ip` | The whitelisted IPv4 address. Keyword only. |
| `settings` | A ready `Settings` object. Other arguments are applied on top of it. |
| `config_file` | Path to a TOML, YAML or JSON settings file. |
| `http_client` | Your own `httpx.Client` (sync) or `httpx.AsyncClient` (async). |
| any setting | For example `environment="sandbox"`, `default_ttl=600`. See [](settings.md). |

Each client has `dns`, `domains`, `settings`, `base_url` and `environment`, plus the `balances()` method.

```{eval-rst}
.. autoclass:: namecheap_sdk.Namecheap
   :members:
   :inherited-members:
   :exclude-members: settings

.. autoclass:: namecheap_sdk.AsyncNamecheap
   :members:
   :inherited-members:
   :exclude-members: settings
```

## What the methods return

The resource methods are annotated as returning `Any`, because one implementation serves both clients: on `Namecheap` they return the value, on `AsyncNamecheap` a coroutine that resolves to it.

| Method | Returns |
| --- | --- |
| `dns.hosts` | `Hosts` |
| `dns.list` | `list[DNSRecord]` |
| `dns.exists` | `bool` |
| `dns.add` | `list[DNSRecord]`, the records that were added |
| `dns.replace`, `dns.point`, `dns.alias`, `dns.set_txt` | `list[DNSRecord]`, the records now in the set |
| `dns.replace_all` | `None` |
| `dns.delete`, `dns.unpoint` | `int`, how many records were removed |
| `domains.list` | `list[Domain]`, all pages |
| `domains.iter` | iterator of `Domain` (async iterator on the async client) |
| `domains.get` | `DomainInfo` |
| `domains.available` | `Availability` |
| `domains.available_many` | `list[Availability]` |
| `domains.tlds` | `list[Tld]` |
| `domains.nameservers` | `Nameservers` |
| `domains.set_nameservers`, `domains.use_default_nameservers` | `bool`, whether Namecheap confirmed |
| `domains.is_locked` | `bool` |
| `domains.lock`, `domains.unlock` | `bool`, whether Namecheap confirmed |
| `balances` | `Balances` |

## DNS

```{eval-rst}
.. autoclass:: namecheap_sdk.resources.DNS
   :members:

.. autoclass:: namecheap_sdk.resources.AsyncDNS
   :members:
```

## Domains

```{eval-rst}
.. autoclass:: namecheap_sdk.resources.Domains
   :members:
   :inherited-members:

.. autoclass:: namecheap_sdk.resources.AsyncDomains
   :members:
   :inherited-members:
```

## Models

```{eval-rst}
.. autoclass:: namecheap_sdk.DNSRecord
   :members:

.. autoclass:: namecheap_sdk.RecordType
   :members:
   :undoc-members:

.. autoclass:: namecheap_sdk.Hosts
   :members:

.. autoclass:: namecheap_sdk.Domain
   :members:

.. autoclass:: namecheap_sdk.DomainInfo
   :members:

.. autoclass:: namecheap_sdk.Availability
   :members:

.. autoclass:: namecheap_sdk.Tld
   :members:

.. autoclass:: namecheap_sdk.Nameservers
   :members:

.. autoclass:: namecheap_sdk.Balances
   :members:
```

## Settings

```{eval-rst}
.. autofunction:: namecheap_sdk.load_settings

.. autoclass:: namecheap_sdk.Settings
   :members: resolved_base_url, command, resolved_user_agent
```

## Errors

```{eval-rst}
.. autoexception:: namecheap_sdk.NamecheapError
.. autoexception:: namecheap_sdk.APIConnectionError
.. autoexception:: namecheap_sdk.APITimeoutError
.. autoexception:: namecheap_sdk.APIError
.. autoexception:: namecheap_sdk.ValidationError
.. autoexception:: namecheap_sdk.AuthenticationError
.. autoexception:: namecheap_sdk.PermissionDeniedError
.. autoexception:: namecheap_sdk.NotFoundError
.. autoexception:: namecheap_sdk.RateLimitError
.. autoexception:: namecheap_sdk.ServerError
.. autoclass:: namecheap_sdk.APIErrorDetail
   :members:
```

## Messages

```{eval-rst}
.. automodule:: namecheap_sdk.messages
   :members: use, reset, catalog, text
```
