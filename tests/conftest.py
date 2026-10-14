from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest

from namecheap_sdk import AsyncNamecheap, Namecheap

NS = 'xmlns="http://api.namecheap.com/xml.response"'


def ok(command: str, body: str) -> str:
    return (f'<?xml version="1.0" encoding="UTF-8"?><ApiResponse {NS} Status="OK"><Errors />'
            f'<RequestedCommand>{command}</RequestedCommand>'
            f'<CommandResponse Type="{command}">{body}</CommandResponse></ApiResponse>')


def error(number: str, message: str) -> str:
    return (f'<?xml version="1.0" encoding="UTF-8"?><ApiResponse {NS} Status="ERROR">'
            f'<Errors><Error Number="{number}">{message}</Error></Errors></ApiResponse>')


def hosts(*rows: tuple[Any, ...], email: str | None = None) -> str:
    attr = f' EmailType="{email}"' if email else ""
    items = "".join(
        f'<host HostId="{i}" Name="{name}" Type="{kind}" Address="{address}" MXPref="{pref}" TTL="{ttl}" '
        f'IsActive="true" />'
        for i, (name, kind, address, ttl, pref) in enumerate(rows, start=1)
    )
    result = (f'<DomainDNSGetHostsResult Domain="example.com"{attr} IsUsingOurDNS="true">{items}'
              "</DomainDNSGetHostsResult>")
    return ok("namecheap.domains.dns.getHosts", result)


SET_OK = ok("namecheap.domains.dns.setHosts", '<DomainDNSSetHostsResult Domain="example.com" IsSuccess="true" />')


class Recorder:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.responses: list[httpx.Response] = []

    def queue(self, text: str, status: int = 200, headers: dict[str, str] | None = None) -> None:
        self.responses.append(httpx.Response(status, text=text, headers=headers or {}))

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if not self.responses:
            return httpx.Response(200, text=ok("x", ""))
        return self.responses.pop(0)

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]

    def params(self, index: int = -1) -> dict[str, str]:
        request = self.requests[index]
        raw = request.content.decode() if request.method == "POST" else request.url.query.decode()
        return {key: values[0] for key, values in parse_qs(raw, keep_blank_values=True).items()}

    def commands(self) -> list[str]:
        return [self.params(i)["Command"] for i in range(len(self.requests))]


@pytest.fixture
def api() -> Recorder:
    return Recorder()


def _client(cls: Any, transport: Any, api: Recorder) -> Any:
    http = transport(transport=httpx.MockTransport(api))
    client = cls("apiuser", "secret", client_ip="203.0.113.5", http_client=http, max_retries=2)
    client._wait_for = lambda attempt, retry_after=None: 0.0
    return client


@pytest.fixture
def nc(api: Recorder) -> Namecheap:
    return _client(Namecheap, httpx.Client, api)


@pytest.fixture
def anc(api: Recorder) -> AsyncNamecheap:
    return _client(AsyncNamecheap, httpx.AsyncClient, api)
