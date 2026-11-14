# Retries and timeouts

The SDK retries failures that are likely to go away on their own: rate limits, server errors and dropped connections.

## What is retried

| Failure | Retried? | Wait |
| --- | --- | --- |
| `RateLimitError` (Namecheap says there are too many requests, or HTTP 429) | Yes | The `Retry-After` header when there is one and it is within `max_retry_wait`, otherwise exponential backoff. |
| `ServerError` (HTTP 5xx, registry errors, broken XML) | Yes | Exponential backoff. |
| `APIConnectionError`, `APITimeoutError` | Yes | Exponential backoff. |
| Any other error | No | |

Unlike the REST based sibling SDKs, Namecheap retries **every** command, writes included. That is safe here: every command this SDK sends can be repeated without harm, because `setHosts` always sends the complete zone. Sending the same full zone twice leaves the same zone.

When the retries run out, the last error is raised.

## The settings

| Setting | Default | Meaning |
| --- | --- | --- |
| `max_retries` | `3` | Retries after the first attempt. `0` turns them off. |
| `max_retry_wait` | `60` | Longest wait in seconds the client accepts between retries. A rate limit that asks for longer is raised at once. |
| `backoff_base` | `1` | First backoff delay in seconds, doubled on every retry. |
| `backoff_cap` | `16` | Upper limit for one backoff delay. |
| `timeout` | `30` | Seconds to wait for one request, for the HTTP client the SDK creates. |

```python
nc = Namecheap(timeout=10, max_retries=5)
```

The wait for retry number `n` (from 0) is:

```text
min(backoff_cap, backoff_base * 2 ** n) + random(0, backoff_base / 2)
```

With the defaults that is about 1, 2, 4, 8 and then 16 seconds, plus a little jitter.

## Namecheap's limits

Namecheap does not publish its limits in the API docs. Its support has quoted around 20 calls per minute, 700 per hour and 8,000 per day for one key. Remember that every DNS write is **two** calls, a `getHosts` and a `setHosts`, while a write that changes nothing is one.

For bulk work:

- Change many records of one domain with a single `add` or `replace_all` instead of many `point` calls.
- Space out loops over many domains, for example `time.sleep(3)` between domains.
- Run big jobs at night and spread them over hours rather than minutes.

## Turning retries off

```python
nc = Namecheap(max_retries=0)
```

Useful in tests, or when a job queue already retries failed jobs.

## Timeouts

`timeout` covers connecting, sending and reading, and is used for the client the SDK creates. A timeout is retried like a dropped connection. With your own `http_client=`, its timeout applies instead, see [](http-client.md).
