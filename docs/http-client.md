# Custom HTTP client

By default `Namecheap` creates its own `httpx.Client` (and `AsyncNamecheap` its own `httpx.AsyncClient`) with the `timeout` from the settings. You can hand it one you built yourself with `http_client=`. That is the place for proxies, custom TLS settings, event hooks for logging, or a mock transport in tests.

## Passing your own client

```python
import httpx

from namecheap_sdk import Namecheap

http = httpx.Client(timeout=20, proxy="http://proxy.internal:3128")
nc = Namecheap("api_user", "API_KEY", client_ip="203.0.113.5", http_client=http)
```

The `proxy=` argument needs httpx 0.26 or newer. Older versions call it `proxies=`.

The async client needs an `httpx.AsyncClient`:

```python
import httpx

from namecheap_sdk import AsyncNamecheap

http = httpx.AsyncClient(timeout=20)
nc = AsyncNamecheap("api_user", "API_KEY", client_ip="203.0.113.5", http_client=http)
```

## Who closes it

The SDK only closes clients it created. If you pass `http_client=`, closing `Namecheap` (or leaving its `with` block) leaves your `httpx.Client` open, so you can share it with other code. Close it yourself when you are done:

```python
with httpx.Client(timeout=20) as http:
    with Namecheap("api_user", "API_KEY", client_ip="203.0.113.5", http_client=http) as nc:
        nc.dns.list("example.com")
```

## Timeouts

When you bring your own client, its timeout is the one that counts. The `timeout` setting is only used for the client the SDK creates. `httpx.Timeout` lets you set the connect, read, write and pool limits separately:

```python
http = httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0))
```

## Logging every request

httpx event hooks run for each request and response. This prints a line per call, which helps while you debug a script:

```python
import httpx

from namecheap_sdk import Namecheap


def show_request(request: httpx.Request) -> None:
    print(">>", request.method, request.url.path)


def show_response(response: httpx.Response) -> None:
    print("<<", response.status_code, response.request.url.path)


http = httpx.Client(event_hooks={"request": [show_request], "response": [show_response]})
nc = Namecheap("api_user", "API_KEY", client_ip="203.0.113.5", http_client=http)
```

```{warning}
Namecheap expects the credentials as request parameters. For read calls they are in the query string, so `request.url` contains your API key. Log `request.url.path` and the `Command` parameter, never the full URL.
```

## Proxies and corporate networks

httpx reads the standard `HTTP_PROXY`, `HTTPS_PROXY` and `NO_PROXY` environment variables on its own, so in many setups you do not need `http_client=` at all. Pass a client when the proxy needs settings the environment cannot express, or when your company uses its own certificate authority:

```python
http = httpx.Client(verify="/etc/ssl/certs/company-ca.pem")
```

## Retries still apply

Retries, backoff and error mapping happen in the SDK, above httpx. A custom client changes how each request is sent, not how failures are handled. See [](retries-timeouts.md).
