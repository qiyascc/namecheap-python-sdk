from __future__ import annotations

from datetime import date
from decimal import Decimal

from conftest import ok


def page(*names: str, total: int) -> str:
    rows = "".join(f'<Domain ID="{i}" Name="{n}" User="owner" Created="02/15/2016" Expires="02/15/2027" '
                   f'IsExpired="false" IsLocked="true" AutoRenew="true" WhoisGuard="ENABLED" IsPremium="false" '
                   f'IsOurDNS="true"/>' for i, n in enumerate(names, 1))
    return ok("namecheap.domains.getList", f"<DomainGetListResult>{rows}</DomainGetListResult>"
              f"<Paging><TotalItems>{total}</TotalItems><CurrentPage>1</CurrentPage><PageSize>100</PageSize></Paging>")


def test_list_pages(nc, api):
    nc.settings.page_size = 2
    api.queue(page("a.com", "b.com", total=3))
    api.queue(page("c.com", total=3))
    domains = nc.domains.list(list_type="expiring", sort_by="name")
    assert [d.name for d in domains] == ["a.com", "b.com", "c.com"]
    assert domains[0].expires == date(2027, 2, 15) and domains[0].is_locked
    first = api.params(0)
    assert (first["ListType"], first["SortBy"], first["Page"], first["PageSize"]) == ("EXPIRING", "NAME", "1", "2")
    assert api.params(1)["Page"] == "2"
    api.queue(page("a.com", total=1))
    assert [d.name for d in nc.domains.iter()] == ["a.com"]


def test_info_check_tlds(nc, api):
    api.queue(ok("namecheap.domains.getinfo",
                 '<DomainGetInfoResult Status="Ok" ID="736542" DomainName="domain1.com" OwnerName="apiuser" '
                 'IsOwner="true" IsPremium="false"><DomainDetails><CreatedDate>09/05/2016</CreatedDate>'
                 '<ExpiredDate>09/05/2027</ExpiredDate></DomainDetails><Whoisguard Enabled="True"><ID>1</ID>'
                 '</Whoisguard><DnsDetails ProviderType="FREE" /></DomainGetInfoResult>'))
    info = nc.domains.get("domain1.com")
    assert (info.id, info.is_owner, info.expires, info.whois_guard, info.dns_provider) == (
        736542, True, date(2027, 9, 5), True, "FREE")

    api.queue(ok("namecheap.domains.check",
                 '<DomainCheckResult Domain="us.xyz" Available="true" ErrorNo="0" Description="" IsPremiumName="true" '
                 'PremiumRegistrationPrice="13000.0000" PremiumRenewalPrice="13000.0000" PremiumRestorePrice="65.0000" '
                 'PremiumTransferPrice="13000.0000" IcannFee="0.0000" EapFee="0.0000"/>'
                 '<DomainCheckResult Domain="testapi.xyz" Available="false" ErrorNo="0" Description="" '
                 'IsPremiumName="false" PremiumRegistrationPrice="0" PremiumRenewalPrice="0" PremiumRestorePrice="0" '
                 'PremiumTransferPrice="0" IcannFee="0" EapFee="0"/>'))
    results = nc.domains.available_many(["us.xyz", "testapi.xyz"])
    assert api.params()["DomainList"] == "us.xyz,testapi.xyz"
    assert (results[0].premium, results[0].registration_price) == (True, Decimal("13000.0000"))
    assert (results[1].available, results[1].registration_price) == (False, None)

    api.queue(ok("namecheap.domains.getTldList",
                 '<Tlds><Tld Name="biz" MinRegisterYears="1" MaxRegisterYears="10" IsApiRegisterable="true" '
                 'IsApiRenewable="true" IsApiTransferable="false" Type="GTLD" IsSupportsIDN="false">US Business</Tld>'
                 '</Tlds>'))
    tld = nc.domains.tlds()[0]
    assert (tld.name, tld.description, tld.api_registerable, tld.max_years) == ("biz", "US Business", True, 10)


def test_nameservers_and_lock(nc, api):
    api.queue(ok("namecheap.domains.dns.getList", '<DomainDNSGetListResult Domain="domain.com" IsUsingOurDNS="false">'
                 '<Nameserver>dns1.name-servers.com</Nameserver><Nameserver>dns2.name-servers.com</Nameserver>'
                 '</DomainDNSGetListResult>'))
    result = nc.domains.nameservers("domain.com")
    assert (result.servers, result.using_our_dns) == (["dns1.name-servers.com", "dns2.name-servers.com"], False)

    api.queue(ok("namecheap.domains.dns.setCustom", '<DomainDNSSetCustomResult Domain="domain.com" Updated="true" />'))
    assert nc.domains.set_nameservers("domain.com", ["ns1.example.net.", "ns2.example.net"]) is True
    assert api.params()["NameServers"] == "ns1.example.net,ns2.example.net"

    reset = '<DomainDNSSetDefaultResult Domain="domain.com" Updated="true" />'
    api.queue(ok("namecheap.domains.dns.setDefault", reset))
    assert nc.domains.use_default_nameservers("domain.com") is True

    api.queue(ok("namecheap.domains.getRegistrarLock",
                 '<DomainGetRegistrarLockResult Domain="domain1.com" RegistrarLockStatus="false" />'))
    assert nc.domains.is_locked("domain1.com") is False
    unlocked = '<DomainSetRegistrarLockResult Domain="d.com" IsSuccess="true" />'
    api.queue(ok("namecheap.domains.setRegistrarLock", unlocked))
    assert nc.domains.unlock("d.com") is True
    assert api.params()["LockAction"] == "UNLOCK"


def test_balances(nc, api):
    api.queue(ok("namecheap.users.getBalances",
                 '<UserGetBalancesResult Currency="USD" AvailableBalance="4932.96" AccountBalance="4932.96" '
                 'EarnedAmount="381.70" WithdrawableAmount="1243.36" FundsRequiredForAutoRenew="0.00" />'))
    balances = nc.balances()
    assert (balances.currency, balances.available) == ("USD", Decimal("4932.96"))
