# Async

`AsyncNamecheap` is the async twin of `Namecheap`. It takes the same arguments, reads the same settings and has the same methods with the same parameters. The only difference is that every call that talks to the API is a coroutine you `await`.

## A first async script

```python
import asyncio

from namecheap_sdk import AsyncNamecheap


async def main() -> None:
    async with AsyncNamecheap() as nc:
        records = await nc.dns.list("example.com", "A")
        for record in records:
            print(record.name, record.data)

        await nc.dns.point("example.com", "shop", "203.0.113.10")


asyncio.run(main())
```

`async with` closes the underlying `httpx.AsyncClient` when the block ends. Without it, call `await nc.close()` yourself.

## Iterating

`domains.iter()` is an async generator on the async client. Use `async for`:

```python
async with AsyncNamecheap() as nc:
    async for domain in nc.domains.iter():
        print(domain.name)
```

Everything else returns a plain value once awaited: `await nc.dns.list(...)` is a `list[DNSRecord]`, `await nc.balances()` a `Balances`.

## Running calls side by side

Because the client is async, several requests can be in flight at once. `asyncio.gather` is the simplest way:

```python
import asyncio

from namecheap_sdk import AsyncNamecheap

SUBDOMAINS = {"shop": "203.0.113.10", "blog": "203.0.113.11", "api": "203.0.113.12"}


async def main() -> None:
    async with AsyncNamecheap() as nc:
        await asyncio.gather(*(
            nc.dns.point("example.com", name, ip) for name, ip in SUBDOMAINS.items()
        ))


asyncio.run(main())
```

```{warning}
Do not run several record changes for the **same domain** side by side. Every change reads the whole zone and writes it back, so two changes in flight at once can each write a zone without the other's record. Change one domain in a loop instead, and run different domains in parallel.
```

The example above changes three names in one zone, so with Namecheap write it as a loop:

```python
for name, ip in SUBDOMAINS.items():
    await nc.dns.point("example.com", name, ip)
```

Or, better, use one `add` or `replace_all` call that carries all the records.

To cap how many requests run at the same time, wrap the calls in a semaphore:

```python
limit = asyncio.Semaphore(3)


async def point(client, name: str, ip: str) -> None:
    async with limit:
        await client.dns.point("example.com", name, ip)
```

## Using it from a web framework

Create one client when the application starts and close it when it stops, instead of building a new one per request. Each client holds a connection pool, and reusing it saves a TLS handshake on every call. [](examples/web-frameworks.md) shows this for FastAPI.

## Mixing sync and async

Do not call the sync `Namecheap` from inside a running event loop, because it blocks the loop while it waits for Namecheap. In async code, use `AsyncNamecheap`. In sync code that needs a one off async call, `asyncio.run()` is fine.

## Errors and retries

The async client raises the same exceptions as the sync one (see [](errors.md)) and retries the same way (see [](retries-timeouts.md)). While it waits between retries it uses `asyncio.sleep`, so other tasks keep running.
