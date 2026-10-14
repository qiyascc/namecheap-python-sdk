from __future__ import annotations

import pytest
from conftest import SET_OK, hosts

from namecheap_sdk import DNSRecord
from namecheap_sdk.resources import split_domain

ZONE = hosts(
    ("@", "A", "203.0.113.1", 1800, 10),
    ("www", "CNAME", "example.com.", 1800, 10),
    ("@", "MX", "mail.example.com.", 1800, 10),
    ("shop", "A", "203.0.113.9", 600, 10),
    email="MX",
)


def written(api) -> list[tuple[str, str, str, str]]:
    params = api.params()
    count = len([k for k in params if k.startswith("HostName")])
    return [(params[f"HostName{i}"], params[f"RecordType{i}"], params[f"Address{i}"], params[f"TTL{i}"])
            for i in range(1, count + 1)]


def test_global_params_and_list(nc, api):
    api.queue(ZONE)
    records = nc.dns.list("Example.com", "A")
    params = api.params()
    assert (params["ApiUser"], params["ApiKey"], params["UserName"], params["ClientIp"]) == (
        "apiuser", "secret", "apiuser", "203.0.113.5")
    assert (params["Command"], params["SLD"], params["TLD"]) == ("namecheap.domains.dns.getHosts", "example", "com")
    assert api.last.method == "GET"
    assert [r.name for r in records] == ["@", "shop"]
    assert records[1] == DNSRecord("A", "shop", "203.0.113.9", 600)
    assert records[1].id == 4


def test_hosts_and_split(nc, api):
    api.queue(ZONE)
    result = nc.dns.hosts("example.com")
    assert (result.email_type, result.using_our_dns, len(result.records)) == ("MX", True, 4)
    assert result.records[2].priority == 10
    assert split_domain("shop.co.uk") == ("shop", "co.uk")
    with pytest.raises(ValueError):
        split_domain("localhost")


def test_point_rewrites_whole_zone(nc, api):
    api.queue(ZONE)
    api.queue(SET_OK)
    nc.dns.point("example.com", "shop", "203.0.113.10")
    assert api.commands() == ["namecheap.domains.dns.getHosts", "namecheap.domains.dns.setHosts"]
    assert api.last.method == "POST"
    assert written(api) == [
        ("@", "A", "203.0.113.1", "1800"),
        ("www", "CNAME", "example.com.", "1800"),
        ("@", "MX", "mail.example.com.", "1800"),
        ("shop", "A", "203.0.113.10", "1800"),
    ]
    params = api.params()
    assert (params["EmailType"], params["MXPref3"]) == ("MX", "10")
    assert "MXPref4" not in params


def test_no_write_when_nothing_changes(nc, api):
    api.queue(ZONE)
    nc.dns.point("example.com", "shop", "203.0.113.9", ttl=600)
    assert api.commands() == ["namecheap.domains.dns.getHosts"]
    api.queue(ZONE)
    assert nc.dns.add("example.com", DNSRecord.a("shop", "203.0.113.9")) == []
    assert len(api.requests) == 2


def test_add_replace_delete(nc, api):
    api.queue(ZONE)
    api.queue(SET_OK)
    added = nc.dns.add("example.com", DNSRecord.txt("@", "v=spf1 -all"), DNSRecord.a("www.example.com", "203.0.113.2"))
    assert [r.name for r in added] == ["@", "www"]
    assert written(api)[-2:] == [("@", "TXT", "v=spf1 -all", "1800"), ("www", "A", "203.0.113.2", "1800")]

    api.queue(ZONE)
    api.queue(SET_OK)
    nc.dns.replace("example.com", "A", "@", ["203.0.113.1", "203.0.113.3"], ttl=300)
    assert written(api)[:2] == [("@", "A", "203.0.113.1", "300"), ("@", "A", "203.0.113.3", "300")]

    api.queue(ZONE)
    api.queue(SET_OK)
    assert nc.dns.delete("example.com", "MX", "@") == 1
    assert [row[1] for row in written(api)] == ["A", "CNAME", "A"]
    assert "EmailType" not in api.params()

    api.queue(ZONE)
    api.queue(SET_OK)
    nc.dns.alias("example.com", "docs", "example.github.io")
    assert written(api)[-1] == ("docs", "CNAME", "example.github.io.", "1800")


def test_email_forwarding_is_kept(nc, api):
    api.queue(hosts(("@", "A", "203.0.113.1", 1800, 10), email="FWD"))
    api.queue(SET_OK)
    nc.dns.set_txt("example.com", "_acme-challenge", "token", ttl=60)
    assert api.params()["EmailType"] == "FWD"
    api.queue(hosts(("@", "A", "203.0.113.1", 1800, 10), email="FWD"))
    api.queue(SET_OK)
    nc.dns.replace_all("example.com", [DNSRecord.a("@", "203.0.113.1")], email_type="OX")
    assert api.params()["EmailType"] == "OX"


def test_ttl_limits_and_helpers(nc):
    with pytest.raises(ValueError):
        nc.dns.add("example.com", DNSRecord.a("x", "203.0.113.1", ttl=30))
    assert DNSRecord.url("old", "https://e.com").type == "URL301"
    assert DNSRecord.url("old", "https://e.com", permanent=False).type == "URL"
    assert DNSRecord.caa("@", "letsencrypt.org").data == '0 issue "letsencrypt.org"'
    assert DNSRecord.mx("@", "mail.example.com", 5).data == "mail.example.com."


def test_set_hosts_failure_is_raised(nc, api):
    from conftest import ok

    from namecheap_sdk import APIError

    api.queue(ZONE)
    failed = '<DomainDNSSetHostsResult Domain="example.com" IsSuccess="false" />'
    api.queue(ok("namecheap.domains.dns.setHosts", failed))
    with pytest.raises(APIError):
        nc.dns.unpoint("example.com", "shop")
