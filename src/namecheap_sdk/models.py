from __future__ import annotations

import ipaddress
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Optional, Union

from .messages import text


class RecordType(str, Enum):
    A = "A"
    AAAA = "AAAA"
    ALIAS = "ALIAS"
    CAA = "CAA"
    CNAME = "CNAME"
    MX = "MX"
    MXE = "MXE"
    NS = "NS"
    TXT = "TXT"
    URL = "URL"
    URL301 = "URL301"
    FRAME = "FRAME"

    def __str__(self) -> str:
        return self.value


RecordTypeLike = Union[RecordType, str]
HOST_TYPES = frozenset({"CNAME", "ALIAS", "NS", "MX"})


def record_type(value: RecordTypeLike) -> str:
    kind = value.value if isinstance(value, RecordType) else str(value).strip().upper()
    if not kind:
        raise ValueError(text("value.empty_type"))
    return kind


def hostname(value: str) -> str:
    host = value.strip()
    if host == "@" or host.endswith(".") or "." not in host:
        return host
    return f"{host}."


def flag(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def number(value: Any) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def money(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def day(value: Any) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), "%m/%d/%Y").date()
    except ValueError:
        return None


def child_text(element: Optional[ET.Element], path: str) -> Optional[str]:
    if element is None:
        return None
    found = element.find(path)
    return found.text.strip() if found is not None and found.text else None


@dataclass
class DNSRecord:
    type: str
    name: str
    data: str
    ttl: Optional[int] = None
    priority: Optional[int] = None
    id: Optional[int] = field(default=None, compare=False)
    active: bool = field(default=True, compare=False)

    def __post_init__(self) -> None:
        self.type = record_type(self.type)
        self.name = self.name.strip() or "@"

    @classmethod
    def a(cls, name: str, ip: str, ttl: Optional[int] = None) -> DNSRecord:
        return cls("A", name, str(ipaddress.IPv4Address(ip)), ttl)

    @classmethod
    def aaaa(cls, name: str, ip: str, ttl: Optional[int] = None) -> DNSRecord:
        return cls("AAAA", name, str(ipaddress.IPv6Address(ip)), ttl)

    @classmethod
    def cname(cls, name: str, target: str, ttl: Optional[int] = None) -> DNSRecord:
        return cls("CNAME", name, hostname(target), ttl)

    @classmethod
    def alias(cls, name: str, target: str, ttl: Optional[int] = None) -> DNSRecord:
        return cls("ALIAS", name, hostname(target), ttl)

    @classmethod
    def txt(cls, name: str, value: str, ttl: Optional[int] = None) -> DNSRecord:
        return cls("TXT", name, value, ttl)

    @classmethod
    def mx(cls, name: str, host: str, priority: int = 10, ttl: Optional[int] = None) -> DNSRecord:
        return cls("MX", name, hostname(host), ttl, priority=priority)

    @classmethod
    def ns(cls, name: str, host: str, ttl: Optional[int] = None) -> DNSRecord:
        return cls("NS", name, hostname(host), ttl)

    @classmethod
    def caa(cls, name: str, value: str, tag: str = "issue", flags: int = 0, ttl: Optional[int] = None) -> DNSRecord:
        return cls("CAA", name, f'{flags} {tag} "{value}"', ttl)

    @classmethod
    def url(cls, name: str, target: str, *, permanent: bool = True, ttl: Optional[int] = None) -> DNSRecord:
        return cls("URL301" if permanent else "URL", name, target, ttl)

    @classmethod
    def frame(cls, name: str, target: str, ttl: Optional[int] = None) -> DNSRecord:
        return cls("FRAME", name, target, ttl)

    @classmethod
    def from_xml(cls, element: ET.Element) -> DNSRecord:
        kind = element.get("Type", "")
        return cls(
            type=kind,
            name=element.get("Name", "@"),
            data=element.get("Address", ""),
            ttl=number(element.get("TTL")),
            priority=number(element.get("MXPref")) if kind.upper() in ("MX", "MXE") else None,
            id=number(element.get("HostId")),
            active=element.get("IsActive", "true").lower() != "false",
        )

    def fqdn(self, domain: str) -> str:
        return domain if self.name == "@" else f"{self.name}.{domain}"


@dataclass
class Hosts:
    domain: str
    records: list[DNSRecord] = field(default_factory=list)
    using_our_dns: bool = True
    email_type: Optional[str] = None

    @classmethod
    def from_xml(cls, element: ET.Element) -> Hosts:
        result = element.find("DomainDNSGetHostsResult")
        node = result if result is not None else element
        email = node.get("EmailType")
        return cls(
            domain=node.get("Domain", ""),
            records=[DNSRecord.from_xml(host) for host in node.iter("host")]
            + [DNSRecord.from_xml(host) for host in node.iter("Host")],
            using_our_dns=flag(node.get("IsUsingOurDNS", "true")),
            email_type=email.upper() if email else None,
        )


@dataclass
class Domain:
    name: str
    id: Optional[int] = None
    user: str = ""
    created: Optional[date] = None
    expires: Optional[date] = None
    is_expired: bool = False
    is_locked: bool = False
    auto_renew: bool = False
    whois_guard: str = ""
    is_premium: bool = False
    is_our_dns: bool = False

    @classmethod
    def from_xml(cls, element: ET.Element) -> Domain:
        return cls(
            name=element.get("Name", ""),
            id=number(element.get("ID")),
            user=element.get("User", ""),
            created=day(element.get("Created")),
            expires=day(element.get("Expires")),
            is_expired=flag(element.get("IsExpired")),
            is_locked=flag(element.get("IsLocked")),
            auto_renew=flag(element.get("AutoRenew")),
            whois_guard=element.get("WhoisGuard", ""),
            is_premium=flag(element.get("IsPremium")),
            is_our_dns=flag(element.get("IsOurDNS")),
        )


@dataclass
class DomainInfo:
    name: str
    id: Optional[int] = None
    status: str = ""
    owner: str = ""
    is_owner: bool = False
    is_premium: bool = False
    created: Optional[date] = None
    expires: Optional[date] = None
    whois_guard: bool = False
    dns_provider: str = ""

    @classmethod
    def from_xml(cls, element: ET.Element) -> DomainInfo:
        result = element.find("DomainGetInfoResult")
        node = result if result is not None else element
        guard = node.find("Whoisguard")
        dns = node.find("DnsDetails")
        return cls(
            name=node.get("DomainName", ""),
            id=number(node.get("ID")),
            status=node.get("Status", ""),
            owner=node.get("OwnerName", ""),
            is_owner=flag(node.get("IsOwner")),
            is_premium=flag(node.get("IsPremium")),
            created=day(child_text(node, "DomainDetails/CreatedDate")),
            expires=day(child_text(node, "DomainDetails/ExpiredDate")),
            whois_guard=flag(guard.get("Enabled")) if guard is not None else False,
            dns_provider=dns.get("ProviderType", "") if dns is not None else "",
        )


@dataclass
class Availability:
    domain: str
    available: bool
    premium: bool = False
    registration_price: Optional[Decimal] = None
    renewal_price: Optional[Decimal] = None
    restore_price: Optional[Decimal] = None
    transfer_price: Optional[Decimal] = None
    icann_fee: Optional[Decimal] = None
    eap_fee: Optional[Decimal] = None
    description: str = ""

    @classmethod
    def from_xml(cls, element: ET.Element) -> Availability:
        premium = flag(element.get("IsPremiumName"))
        return cls(
            domain=element.get("Domain", ""),
            available=flag(element.get("Available")),
            premium=premium,
            registration_price=money(element.get("PremiumRegistrationPrice")) if premium else None,
            renewal_price=money(element.get("PremiumRenewalPrice")) if premium else None,
            restore_price=money(element.get("PremiumRestorePrice")) if premium else None,
            transfer_price=money(element.get("PremiumTransferPrice")) if premium else None,
            icann_fee=money(element.get("IcannFee")),
            eap_fee=money(element.get("EapFee")),
            description=element.get("Description", ""),
        )


@dataclass
class Tld:
    name: str
    description: str = ""
    type: str = ""
    min_years: Optional[int] = None
    max_years: Optional[int] = None
    api_registerable: bool = False
    api_renewable: bool = False
    api_transferable: bool = False
    supports_idn: bool = False

    @classmethod
    def from_xml(cls, element: ET.Element) -> Tld:
        return cls(
            name=element.get("Name", ""),
            description=(element.text or "").strip(),
            type=element.get("Type", ""),
            min_years=number(element.get("MinRegisterYears")),
            max_years=number(element.get("MaxRegisterYears")),
            api_registerable=flag(element.get("IsApiRegisterable")),
            api_renewable=flag(element.get("IsApiRenewable")),
            api_transferable=flag(element.get("IsApiTransferable")),
            supports_idn=flag(element.get("IsSupportsIDN")),
        )


@dataclass
class Nameservers:
    domain: str
    servers: list[str] = field(default_factory=list)
    using_our_dns: bool = True

    @classmethod
    def from_xml(cls, element: ET.Element) -> Nameservers:
        result = element.find("DomainDNSGetListResult")
        node = result if result is not None else element
        return cls(
            domain=node.get("Domain", ""),
            servers=[(ns.text or "").strip() for ns in node.iter("Nameserver") if ns.text],
            using_our_dns=flag(node.get("IsUsingOurDNS", "true")),
        )


@dataclass
class Balances:
    currency: str
    available: Optional[Decimal] = None
    account: Optional[Decimal] = None
    earned: Optional[Decimal] = None
    withdrawable: Optional[Decimal] = None
    required_for_auto_renew: Optional[Decimal] = None

    @classmethod
    def from_xml(cls, element: ET.Element) -> Balances:
        result = element.find("UserGetBalancesResult")
        node = result if result is not None else element
        return cls(
            currency=node.get("Currency", ""),
            available=money(node.get("AvailableBalance")),
            account=money(node.get("AccountBalance")),
            earned=money(node.get("EarnedAmount")),
            withdrawable=money(node.get("WithdrawableAmount")),
            required_for_auto_renew=money(node.get("FundsRequiredForAutoRenew")),
        )
