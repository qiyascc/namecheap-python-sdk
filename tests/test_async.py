from __future__ import annotations

from conftest import SET_OK, hosts, ok


async def test_async_flow(anc, api):
    api.queue(hosts(("@", "A", "203.0.113.1", 1800, 10)))
    api.queue(SET_OK)
    await anc.dns.point("example.com", "shop", "203.0.113.10")
    assert [p for p in api.commands()] == ["namecheap.domains.dns.getHosts", "namecheap.domains.dns.setHosts"]
    api.queue(ok("namecheap.domains.getList", '<DomainGetListResult><Domain Name="a.com" /></DomainGetListResult>'
                 '<Paging><TotalItems>1</TotalItems></Paging>'))
    assert [d.name async for d in anc.domains.iter()] == ["a.com"]
    api.queue(ok("namecheap.users.getBalances", '<UserGetBalancesResult Currency="USD" />'))
    assert (await anc.balances()).currency == "USD"
    await anc.close()
