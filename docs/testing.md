# Testing your code

Code that edits DNS should be tested without real DNS. The client accepts any `httpx` client, so you can plug in `httpx.MockTransport` and answer with the XML Namecheap would send. The SDK's own test suite works this way.

## Building Namecheap answers

Every Namecheap answer has the same envelope. Two helpers cover success and failure:

```python
NS = 'xmlns="http://api.namecheap.com/xml.response"'


def ok(command: str, body: str) -> str:
    return (f'<?xml version="1.0" encoding="UTF-8"?><ApiResponse {NS} Status="OK"><Errors />'
            f'<RequestedCommand>{command}</RequestedCommand>'
            f'<CommandResponse Type="{command}">{body}</CommandResponse></ApiResponse>')


def error(number: str, message: str) -> str:
    return (f'<?xml version="1.0" encoding="UTF-8"?><ApiResponse {NS} Status="ERROR">'
            f'<Errors><Error Number="{number}">{message}</Error></Errors></ApiResponse>')


def hosts(*rows) -> str:
    items = "".join(
        f'<host HostId="{i}" Name="{name}" Type="{kind}" Address="{address}" MXPref="10" TTL="{ttl}" IsActive="true" />'
        for i, (name, kind, address, ttl) in enumerate(rows, start=1)
    )
    result = f'<DomainDNSGetHostsResult Domain="example.com" IsUsingOurDNS="true">{items}</DomainDNSGetHostsResult>'
    return ok("namecheap.domains.dns.getHosts", result)


SET_OK = ok("namecheap.domains.dns.setHosts", '<DomainDNSSetHostsResult Domain="example.com" IsSuccess="true" />')
```

## A recorder fixture for pytest

The recorder hands out queued answers and remembers every request. Namecheap puts parameters in the query string for `GET` and in the form body for `POST`, so `params()` reads both:

```python
from urllib.parse import parse_qs

import httpx
import pytest

from namecheap_sdk import Namecheap


class Recorder:
    def __init__(self):
        self.requests = []
        self.responses = []

    def queue(self, text, status=200):
        self.responses.append(httpx.Response(status, text=text))

    def __call__(self, request):
        self.requests.append(request)
        return self.responses.pop(0)

    def params(self, index=-1):
        request = self.requests[index]
        raw = request.content.decode() if request.method == "POST" else request.url.query.decode()
        return {key: values[0] for key, values in parse_qs(raw, keep_blank_values=True).items()}


@pytest.fixture
def api():
    return Recorder()


@pytest.fixture
def nc(api):
    http = httpx.Client(transport=httpx.MockTransport(api))
    client = Namecheap("apiuser", "secret", client_ip="203.0.113.5", http_client=http, max_retries=2)
    client._wait_for = lambda attempt, retry_after=None: 0.0
    return client
```

The last line makes retries instant inside tests. `_wait_for` is internal, so keep it in test code.

## Example tests

The function under test:

```python
def create_customer_site(nc, slug: str) -> str:
    if nc.dns.exists("example.com", "A", slug):
        raise ValueError(f"{slug}.example.com is already taken")
    nc.dns.point("example.com", slug, "203.0.113.10", ttl=300)
    return f"{slug}.example.com"
```

The tests queue a zone, then check what was written:

```python
def test_adds_the_record_and_keeps_the_rest(nc, api):
    api.queue(hosts(("@", "A", "203.0.113.1", 1800)))
    api.queue(hosts(("@", "A", "203.0.113.1", 1800)))
    api.queue(SET_OK)

    assert create_customer_site(nc, "acme") == "acme.example.com"

    sent = api.params()
    assert sent["Command"] == "namecheap.domains.dns.setHosts"
    assert (sent["HostName1"], sent["Address1"]) == ("@", "203.0.113.1")
    assert (sent["HostName2"], sent["Address2"], sent["TTL2"]) == ("acme", "203.0.113.10", "300")


def test_refuses_a_taken_name(nc, api):
    api.queue(hosts(("acme", "A", "198.51.100.1", 1800)))

    with pytest.raises(ValueError):
        create_customer_site(nc, "acme")
    assert len(api.requests) == 1
```

The first test queues the zone twice: once for `exists`, once for the read inside `point`.

## Testing error handling

```python
from namecheap_sdk import NotFoundError


def test_domain_not_in_account(nc, api):
    api.queue(error("2019166", "Domain not found"))

    with pytest.raises(NotFoundError) as caught:
        nc.dns.list("not-mine.com")

    assert caught.value.number == "2019166"
```

## Async tests

```python
import httpx
import pytest

from namecheap_sdk import AsyncNamecheap


@pytest.fixture
def anc(api):
    http = httpx.AsyncClient(transport=httpx.MockTransport(api))
    client = AsyncNamecheap("apiuser", "secret", client_ip="203.0.113.5", http_client=http, max_retries=2)
    client._wait_for = lambda attempt, retry_after=None: 0.0
    return client


@pytest.mark.asyncio
async def test_async_point(anc, api):
    api.queue(hosts())
    api.queue(SET_OK)
    await anc.dns.point("example.com", "shop", "203.0.113.10")
    assert api.params()["Address1"] == "203.0.113.10"
```

## End to end against the sandbox

Before a release, run a few tests against Namecheap's sandbox with a sandbox account and a domain registered there. Keep them out of the normal suite:

```python
import os

import pytest

from namecheap_sdk import Namecheap

pytestmark = pytest.mark.skipif("NAMECHEAP_SANDBOX_KEY" not in os.environ, reason="no sandbox key")


def test_sandbox_roundtrip():
    with Namecheap(os.environ["NAMECHEAP_SANDBOX_USER"], os.environ["NAMECHEAP_SANDBOX_KEY"],
                   client_ip=os.environ["NAMECHEAP_CLIENT_IP"], environment="sandbox") as nc:
        nc.balances()
```
