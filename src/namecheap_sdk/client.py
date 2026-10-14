from __future__ import annotations

from typing import Any

from ._base import AsyncClient, Call, SyncClient
from .models import Balances
from .resources import DNS, AsyncDNS, AsyncDomains, Domains


class Namecheap(SyncClient):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.domains = Domains(self)
        self.dns = DNS(self)

    def balances(self) -> Balances:
        result: Balances = self._execute(Call(self.settings.command("balances"), parse=Balances.from_xml))
        return result


class AsyncNamecheap(AsyncClient):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.domains = AsyncDomains(self)
        self.dns = AsyncDNS(self)

    async def balances(self) -> Balances:
        result: Balances = await self._execute(Call(self.settings.command("balances"), parse=Balances.from_xml))
        return result
