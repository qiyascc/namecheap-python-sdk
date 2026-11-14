# Errors

Namecheap answers **HTTP 200 even when a call fails**, and puts the failure inside the XML as `Status="ERROR"` with one or more numbered errors. The SDK reads that and raises a proper exception, so you never have to inspect XML yourself. Every exception it raises on purpose inherits from {py:class}`~namecheap_sdk.NamecheapError`.

Mistakes in your own arguments, like an empty name, a TTL out of range or an invalid IP address, raise plain `ValueError` before any request is sent.

## The hierarchy

```text
NamecheapError
├── APIConnectionError        the request never got an answer
│   └── APITimeoutError       it timed out
└── APIError                  Namecheap reported an error
    ├── ValidationError       a parameter was rejected
    ├── AuthenticationError   bad credentials, IP not whitelisted, or none configured
    ├── PermissionDeniedError the domain cannot be changed through the API
    ├── NotFoundError         the domain is not found or not in this account
    ├── RateLimitError        too many requests, after the retries ran out
    └── ServerError           5xx answers, broken XML, upstream registry trouble
```

## How errors are classified

Namecheap identifies errors by number. The SDK maps the first error in the answer like this:

| Exception | When |
| --- | --- |
| `RateLimitError` | The message mentions "too many requests" or "rate limit", or HTTP 429. |
| `AuthenticationError` | Error numbers for a wrong user or key, a disabled API or a `ClientIp` that is not whitelisted (for example 1011102, 1011150), HTTP 401, or missing credentials. |
| `NotFoundError` | 2019166 and 2016166: the domain is not found or not in this account. HTTP 404. |
| `PermissionDeniedError` | 2030166 and 4011103: the domain cannot be edited through the API. HTTP 403. |
| `ValidationError` | Known parameter errors (for example 2015278, 3011288) and any other number starting with 2. |
| `ServerError` | Known server and registry errors, any number starting with 5, HTTP 5xx, and answers that are not valid XML. |
| `APIError` | Any other error in the XML. |
| `APIConnectionError`, `APITimeoutError` | No answer at all. |

## What an error carries

| Attribute | Meaning |
| --- | --- |
| `message` | Namecheap's message. When the answer had several errors, their messages joined with `; `. |
| `number` | Namecheap's error number of the first error, as a string, for example `"2019166"`. |
| `errors` | Every error in the answer, as {py:class}`~namecheap_sdk.APIErrorDetail` objects with `number` and `message`. |
| `command` | The command that failed, for example `namecheap.domains.dns.setHosts`. |
| `status_code` | The HTTP status. Usually 200, because that is how Namecheap reports errors. |
| `response` | The raw `httpx.Response`, or `None`. |

`RateLimitError` also has `retry_after`: the seconds from a `Retry-After` header, when there was one.

`str(exc)` gives a compact line:

```text
2019166 Domain not found (namecheap.domains.dns.getHosts)
```

## Handling patterns

### A domain that might not be yours

```python
from namecheap_sdk import Namecheap, NotFoundError

with Namecheap() as nc:
    try:
        records = nc.dns.list("not-mine.com")
    except NotFoundError as exc:
        print(exc.number, exc.message)
```

### Credentials and whitelist problems

```python
from namecheap_sdk import AuthenticationError

try:
    nc.balances()
except AuthenticationError as exc:
    for error in exc.errors:
        print(error.number, error.message)
```

Namecheap's message usually says exactly what is wrong, for example that the IP is not whitelisted. Print `exc.errors` before you go looking elsewhere.

### Retry later or fix the request

```python
from namecheap_sdk import APIConnectionError, APIError, ServerError

try:
    nc.dns.point("example.com", "shop", ip)
except ValueError:
    raise
except (ServerError, APIConnectionError):
    schedule_retry_later()
except APIError as exc:
    log.error("Namecheap refused: %s", exc)
    raise
```

`ValueError` means nothing was sent. `ServerError` and `APIConnectionError` are worth another try later, after the SDK's own retries. Other `APIError`s need a different request.

### When a write is not confirmed

After `setHosts`, Namecheap reports `IsSuccess`. If it says `false`, the SDK raises `APIError` with the message "Namecheap did not confirm the change for example.com". Read the zone again before you retry, to see what state it is in.

## Errors raised before a request

| Error | When |
| --- | --- |
| `AuthenticationError` | Building a client without an API user, an API key or a client IP. |
| `ValueError` | `environment` is not `production`, `prod`, `sandbox` or `test`. |
| `ValueError` | An empty domain, a domain without a TLD, an empty name or type, a name outside the domain, an invalid IP, a TTL outside 60 to 60000, `add()` with no records, `replace()` with no values, `available_many([])`, or fewer than two name servers. |
| `pydantic.ValidationError` | A setting outside its range, for example `page_size=500`. |

The texts of the SDK's own messages can be changed or translated, see [](messages.md).
