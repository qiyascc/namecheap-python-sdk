from __future__ import annotations

import ipaddress
import xml.etree.ElementTree as ET
from typing import Any, Callable, Iterable, Optional, Sequence, Union

from .._base import Call, Flow
from ..errors import APIError
from ..messages import text
from ..models import HOST_TYPES, DNSRecord, Hosts, RecordType, RecordTypeLike, hostname, record_type

RecordValues = Union[str, DNSRecord, Iterable[Union[str, DNSRecord]]]
Change = Callable[[list[DNSRecord]], tuple[list[DNSRecord], Any]]


def domain_name(value: str) -> str:
    name = value.strip().lower().rstrip(".")
    if not name:
        raise ValueError(text("value.empty_domain"))
    return name


def split_domain(value: str) -> tuple[str, str]:
    name = domain_name(value)
    if "." not in name:
        raise ValueError(text("value.no_tld", domain=value))
    sld, tld = name.split(".", 1)
    return sld, tld


def relative_name(name: str, domain: str) -> str:
    value = name.strip().lower()
    if not value:
        raise ValueError(text("value.empty_name"))
    if value in ("@", domain, f"{domain}."):
        return "@"
    bare = value.rstrip(".")
    if bare.endswith(f".{domain}"):
        return bare[: -len(domain) - 1]
    if value.endswith("."):
        raise ValueError(text("value.foreign_name", name=name, domain=domain))
    return value


def ip_record_type(ip: str) -> RecordType:
    return RecordType.A if ipaddress.ip_address(ip).version == 4 else RecordType.AAAA


def email_type(records: Sequence[DNSRecord], current: Optional[str], explicit: Optional[str]) -> Optional[str]:
    if explicit:
        return explicit.strip().upper()
    kinds = {record.type for record in records}
    if "MXE" in kinds:
        return "MXE"
    if "MX" in kinds:
        return "MX"
    if current and current not in ("MX", "MXE", "NONE"):
        return current
    return None


def _same(kind: str, left: str, right: str) -> bool:
    if kind in HOST_TYPES:
        return left.rstrip(".").lower() == right.rstrip(".").lower()
    return left == right


class DNS:
    def __init__(self, client: Any) -> None:
        self._client = client

    def _command(self, name: str) -> str:
        return self._client.settings.command(name)

    def _hosts_call(self, domain: str) -> Call:
        sld, tld = split_domain(domain)
        return Call(self._command("get_hosts"), {"SLD": sld, "TLD": tld}, parse=Hosts.from_xml)

    def _ttl(self, value: Optional[int]) -> int:
        ttl = self._client.settings.default_ttl if value is None else int(value)
        if not 60 <= ttl <= 60000:
            raise ValueError(text("value.ttl_range", ttl=ttl))
        return ttl

    def _prepare(self, zone: str, records: Iterable[DNSRecord]) -> list[DNSRecord]:
        prepared = []
        for record in records:
            copy = DNSRecord(record.type, relative_name(record.name, zone), record.data, record.ttl, record.priority)
            if copy.type in HOST_TYPES:
                copy.data = hostname(copy.data)
            if copy.ttl is not None:
                self._ttl(copy.ttl)
            prepared.append(copy)
        return prepared

    def _set_call(self, domain: str, records: Sequence[DNSRecord], mail: Optional[str]) -> Call:
        sld, tld = split_domain(domain)
        params: dict[str, Any] = {"SLD": sld, "TLD": tld}
        for index, record in enumerate(records, start=1):
            params[f"HostName{index}"] = record.name
            params[f"RecordType{index}"] = record.type
            params[f"Address{index}"] = record.data
            params[f"TTL{index}"] = self._ttl(record.ttl)
            if record.type in ("MX", "MXE"):
                params[f"MXPref{index}"] = record.priority if record.priority is not None else 10
        if mail:
            params["EmailType"] = mail

        def parse(element: ET.Element) -> None:
            result = element.find("DomainDNSSetHostsResult")
            if result is not None and result.get("IsSuccess", "true").lower() == "false":
                raise APIError(text("error.not_saved", domain=domain), command=self._command("set_hosts"))

        return Call(self._command("set_hosts"), params, parse=parse, write=True)

    def _rewrite(self, domain: str, change: Change, mail: Optional[str] = None) -> Flow[Any]:
        current: Hosts = yield self._hosts_call(domain)
        before = list(current.records)
        records, result = change(list(before))
        wanted_mail = email_type(records, current.email_type, mail)
        if records == before and (mail is None or wanted_mail == current.email_type):
            return result
        yield self._set_call(domain, records, wanted_mail)
        return result

    def hosts(self, domain: str) -> Any:
        return self._client._execute(self._hosts_call(domain))

    def list(self, domain: str, type: Optional[RecordTypeLike] = None, name: Optional[str] = None) -> Any:
        zone = domain_name(domain)
        kind = record_type(type) if type is not None else None
        label = relative_name(name, zone) if name else None
        call = self._hosts_call(zone)
        call.parse = lambda element: [r for r in Hosts.from_xml(element).records
                                      if (kind is None or r.type == kind) and (label is None or r.name == label)]
        return self._client._execute(call)

    def exists(self, domain: str, type: RecordTypeLike, name: str) -> Any:
        zone, kind = domain_name(domain), record_type(type)
        label = relative_name(name, zone)
        call = self._hosts_call(zone)
        call.parse = lambda element: any(r.type == kind and r.name == label for r in Hosts.from_xml(element).records)
        return self._client._execute(call)

    def add(self, domain: str, *records: DNSRecord, email_type: Optional[str] = None) -> Any:
        if not records:
            raise ValueError(text("value.add_needs_records"))
        zone = domain_name(domain)
        new = self._prepare(zone, records)

        def change(current: list[DNSRecord]) -> tuple[list[DNSRecord], list[DNSRecord]]:
            added = [r for r in new if not any(o.type == r.type and o.name == r.name and _same(r.type, o.data, r.data)
                                               for o in current)]
            return current + added, added

        return self._client._drive(self._rewrite(zone, change, email_type))

    def replace(
        self, domain: str, type: RecordTypeLike, name: str, values: RecordValues, *, ttl: Optional[int] = None
    ) -> Any:
        zone, kind = domain_name(domain), record_type(type)
        label = relative_name(name, zone)
        if isinstance(values, (str, DNSRecord)):
            values = [values]
        wanted = [v if isinstance(v, DNSRecord) else DNSRecord(kind, label, str(v), ttl) for v in values]
        if not wanted:
            raise ValueError(text("value.no_values"))
        for record in wanted:
            record.type, record.name = kind, label
            if record.ttl is None:
                record.ttl = ttl
        wanted = self._prepare(zone, wanted)

        def change(current: list[DNSRecord]) -> tuple[list[DNSRecord], list[DNSRecord]]:
            old = [r for r in current if r.type == kind and r.name == label]
            for record in wanted:
                match = next((o for o in old if _same(kind, o.data, record.data)), None)
                if record.ttl is None and match is not None:
                    record.ttl = match.ttl
                if record.priority is None and match is not None:
                    record.priority = match.priority
            position = next((i for i, r in enumerate(current) if r.type == kind and r.name == label), len(current))
            kept = [r for r in current if not (r.type == kind and r.name == label)]
            index = min(position, len(kept))
            return kept[:index] + wanted + kept[index:], wanted

        return self._client._drive(self._rewrite(zone, change))

    def replace_all(self, domain: str, records: Sequence[DNSRecord], *, email_type: Optional[str] = None) -> Any:
        zone = domain_name(domain)
        new = self._prepare(zone, records)
        return self._client._drive(self._rewrite(zone, lambda current: (new, None), email_type))

    def delete(self, domain: str, type: RecordTypeLike, name: str, data: Optional[str] = None) -> Any:
        zone, kind = domain_name(domain), record_type(type)
        label = relative_name(name, zone)

        def gone(record: DNSRecord) -> bool:
            return record.type == kind and record.name == label and (data is None or _same(kind, record.data, data))

        def change(current: list[DNSRecord]) -> tuple[list[DNSRecord], int]:
            kept = [r for r in current if not gone(r)]
            return kept, len(current) - len(kept)

        return self._client._drive(self._rewrite(zone, change))

    def point(self, domain: str, name: str, ip: str, *, ttl: Optional[int] = None) -> Any:
        address = str(ipaddress.ip_address(ip))
        return self.replace(domain, ip_record_type(address), name, [address], ttl=ttl)

    def unpoint(self, domain: str, name: str, ip_version: int = 4) -> Any:
        return self.delete(domain, RecordType.A if ip_version == 4 else RecordType.AAAA, name)

    def alias(self, domain: str, name: str, target: str, *, ttl: Optional[int] = None) -> Any:
        return self.replace(domain, RecordType.CNAME, name, [target], ttl=ttl)

    def set_txt(self, domain: str, name: str, values: Union[str, Iterable[str]], *, ttl: Optional[int] = None) -> Any:
        return self.replace(domain, RecordType.TXT, name, values, ttl=ttl)


class AsyncDNS(DNS):
    pass
