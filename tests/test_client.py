from __future__ import annotations

import httpx
import pytest
from conftest import error, ok

from namecheap_sdk import (
    APIConnectionError,
    AuthenticationError,
    Namecheap,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ServerError,
    ValidationError,
    load_settings,
)


def test_missing_credentials(monkeypatch, tmp_path):
    for name in ("NAMECHEAP_API_USER", "NAMECHEAP_API_KEY", "NAMECHEAP_CLIENT_IP"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(AuthenticationError):
        Namecheap("user", "key")


def test_env_file_and_environments(monkeypatch, tmp_path):
    monkeypatch.setenv("NAMECHEAP_API_USER", "envuser")
    monkeypatch.setenv("NAMECHEAP_API_KEY", "envkey")
    monkeypatch.setenv("NAMECHEAP_CLIENT_IP", "198.51.100.7")
    client = Namecheap(environment="sandbox", username="customer")
    assert client.base_url == "https://api.sandbox.namecheap.com/xml.response"
    assert client._credentials == {"ApiUser": "envuser", "ApiKey": "envkey", "UserName": "customer",
                                   "ClientIp": "198.51.100.7"}
    path = tmp_path / "nc.json"
    path.write_text('{"api_user": "f", "api_key": "k", "client_ip": "192.0.2.1", "default_ttl": 300}')
    monkeypatch.delenv("NAMECHEAP_API_USER")
    assert Namecheap(config_file=str(path)).settings.default_ttl == 300
    with pytest.raises(ValueError):
        load_settings(api_user="u", api_key="k", client_ip="1.1.1.1", environment="moon").resolved_base_url()


def test_command_override(monkeypatch, api):
    monkeypatch.setenv("NAMECHEAP_COMMANDS__BALANCES", "namecheap.users.getBalancesV2")
    client = Namecheap("u", "k", client_ip="1.1.1.1", http_client=httpx.Client(transport=httpx.MockTransport(api)))
    api.queue(ok("x", '<UserGetBalancesResult Currency="USD" />'))
    client.balances()
    assert api.params()["Command"] == "namecheap.users.getBalancesV2"


@pytest.mark.parametrize("number,message,cls", [
    ("1011150", "Parameter RequestIP is invalid", AuthenticationError),
    ("2019166", "Domain not found", NotFoundError),
    ("2030166", "Edit permission for domain is not supported", PermissionDeniedError),
    ("3013288", "Too many records", ValidationError),
])
def test_xml_errors(nc, api, number, message, cls):
    api.queue(error(number, message))
    with pytest.raises(cls) as info:
        nc.dns.hosts("example.com")
    assert (info.value.number, info.value.message, info.value.command) == (
        number, message, "namecheap.domains.dns.getHosts")
    assert number in str(info.value)


def test_too_many_requests_is_retried(nc, api):
    api.queue(error("500000", "Too many requests"))
    api.queue(ok("namecheap.users.getBalances", '<UserGetBalancesResult Currency="USD" />'))
    assert nc.balances().currency == "USD"
    for _ in range(3):
        api.queue(error("500000", "Too many requests"))
    with pytest.raises(RateLimitError):
        nc.balances()


def test_server_errors_and_bad_xml(nc, api):
    api.queue("oops", status=503)
    api.queue(ok("namecheap.users.getBalances", '<UserGetBalancesResult Currency="EUR" />'))
    assert nc.balances().currency == "EUR"
    for _ in range(3):
        api.queue("<html>not xml")
    with pytest.raises(ServerError):
        nc.balances()


def test_connection_error():
    def boom(request):
        raise httpx.ConnectError("down")

    client = Namecheap("u", "k", client_ip="1.1.1.1", max_retries=0,
                       http_client=httpx.Client(transport=httpx.MockTransport(boom)))
    with pytest.raises(APIConnectionError):
        client.balances()
