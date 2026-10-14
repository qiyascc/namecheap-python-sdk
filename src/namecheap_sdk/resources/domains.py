from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any, AsyncIterator, Iterable, Iterator, Optional

from .._base import Call, Flow
from ..messages import text
from ..models import Availability, Domain, DomainInfo, Nameservers, Tld, flag, number
from .dns import domain_name, split_domain


def _page(element: ET.Element) -> tuple[list[Domain], int]:
    rows = [Domain.from_xml(row) for row in element.iter("Domain")]
    total = number(element.findtext("Paging/TotalItems")) or 0
    return rows, total


def _updated(tag: str, attribute: str) -> Any:
    def parse(element: ET.Element) -> bool:
        node = element.find(tag)
        return flag(node.get(attribute)) if node is not None else True

    return parse


class _DomainsBase:
    def __init__(self, client: Any) -> None:
        self._client = client

    def _command(self, name: str) -> str:
        return self._client.settings.command(name)

    def _run(self, call: Call) -> Any:
        return self._client._execute(call)

    def _page_call(self, page: int, list_type: str, search: Optional[str], sort_by: Optional[str]) -> Call:
        params = {"ListType": list_type.upper(), "SearchTerm": search, "SortBy": sort_by.upper() if sort_by else None,
                  "Page": page, "PageSize": self._client.settings.page_size}
        return Call(self._command("list_domains"), params, parse=_page)

    def list(self, *, list_type: str = "ALL", search: Optional[str] = None, sort_by: Optional[str] = None) -> Any:
        size = self._client.settings.page_size

        def flow() -> Flow[list[Domain]]:
            found: list[Domain] = []
            page = 1
            while True:
                rows, total = yield self._page_call(page, list_type, search, sort_by)
                found.extend(rows)
                if not rows or page * size >= total:
                    return found
                page += 1

        return self._client._drive(flow())

    def get(self, domain: str) -> Any:
        return self._run(Call(self._command("domain_info"), {"DomainName": domain_name(domain)},
                              parse=DomainInfo.from_xml))

    def available(self, domain: str) -> Any:
        call = Call(self._command("check"), {"DomainList": domain_name(domain)},
                    parse=lambda element: Availability.from_xml(next(element.iter("DomainCheckResult"))))
        return self._run(call)

    def available_many(self, domains: Iterable[str]) -> Any:
        names = [domain_name(d) for d in domains]
        if not names:
            raise ValueError(text("value.no_domains"))
        parse = lambda element: [Availability.from_xml(row) for row in element.iter("DomainCheckResult")]
        return self._run(Call(self._command("check"), {"DomainList": names}, parse=parse))

    def tlds(self) -> Any:
        parse = lambda element: [Tld.from_xml(row) for row in element.iter("Tld")]
        return self._run(Call(self._command("tlds"), parse=parse))

    def nameservers(self, domain: str) -> Any:
        sld, tld = split_domain(domain)
        return self._run(Call(self._command("get_nameservers"), {"SLD": sld, "TLD": tld}, parse=Nameservers.from_xml))

    def set_nameservers(self, domain: str, servers: Iterable[str]) -> Any:
        names = [server.strip().rstrip(".") for server in servers if server.strip()]
        if len(names) < 2:
            raise ValueError(text("value.nameserver_count", count=len(names)))
        sld, tld = split_domain(domain)
        call = Call(self._command("set_custom_nameservers"), {"SLD": sld, "TLD": tld, "NameServers": names},
                    parse=_updated("DomainDNSSetCustomResult", "Updated"))
        return self._run(call)

    def use_default_nameservers(self, domain: str) -> Any:
        sld, tld = split_domain(domain)
        call = Call(self._command("set_default_nameservers"), {"SLD": sld, "TLD": tld},
                    parse=_updated("DomainDNSSetDefaultResult", "Updated"))
        return self._run(call)

    def is_locked(self, domain: str) -> Any:
        call = Call(self._command("get_lock"), {"DomainName": domain_name(domain)},
                    parse=_updated("DomainGetRegistrarLockResult", "RegistrarLockStatus"))
        return self._run(call)

    def lock(self, domain: str) -> Any:
        return self._set_lock(domain, "LOCK")

    def unlock(self, domain: str) -> Any:
        return self._set_lock(domain, "UNLOCK")

    def _set_lock(self, domain: str, action: str) -> Any:
        call = Call(self._command("set_lock"), {"DomainName": domain_name(domain), "LockAction": action},
                    parse=_updated("DomainSetRegistrarLockResult", "IsSuccess"))
        return self._run(call)


class Domains(_DomainsBase):
    def iter(self, *, list_type: str = "ALL", search: Optional[str] = None,
             sort_by: Optional[str] = None) -> Iterator[Domain]:
        size = self._client.settings.page_size
        page = 1
        while True:
            rows, total = self._client._execute(self._page_call(page, list_type, search, sort_by))
            yield from rows
            if not rows or page * size >= total:
                return
            page += 1


class AsyncDomains(_DomainsBase):
    async def iter(self, *, list_type: str = "ALL", search: Optional[str] = None,
                   sort_by: Optional[str] = None) -> AsyncIterator[Domain]:
        size = self._client.settings.page_size
        page = 1
        while True:
            rows, total = await self._client._execute(self._page_call(page, list_type, search, sort_by))
            for row in rows:
                yield row
            if not rows or page * size >= total:
                return
            page += 1
