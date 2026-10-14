from __future__ import annotations

import asyncio
import random
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Callable, Generator, Mapping, Optional, TypeVar

import httpx

from .config import Settings, load_settings
from .errors import (
    APIConnectionError,
    APIError,
    APIErrorDetail,
    APITimeoutError,
    RateLimitError,
    ServerError,
    from_details,
    from_status,
)
from .messages import text

T = TypeVar("T")

def parse_xml(content: str) -> ET.Element:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ServerError(text("error.bad_xml", error=exc)) from exc
    for element in root.iter():
        if isinstance(element.tag, str) and "}" in element.tag:
            element.tag = element.tag.split("}", 1)[1]
    return root


@dataclass
class Call:
    command: str
    params: Optional[Mapping[str, Any]] = None
    parse: Callable[[ET.Element], Any] = lambda element: element
    write: bool = False

    def clean_params(self) -> dict[str, str]:
        cleaned: dict[str, str] = {}
        for key, value in (self.params or {}).items():
            if value is None:
                continue
            if isinstance(value, bool):
                cleaned[key] = "true" if value else "false"
            elif isinstance(value, (list, tuple, set, frozenset)):
                cleaned[key] = ",".join(str(v) for v in value)
            else:
                cleaned[key] = str(value)
        return cleaned


Flow = Generator[Call, Any, T]


class BaseClient:
    def __init__(
        self,
        api_user: Optional[str] = None,
        api_key: Optional[str] = None,
        *,
        client_ip: Optional[str] = None,
        settings: Optional[Settings] = None,
        config_file: Optional[str] = None,
        **overrides: Any,
    ) -> None:
        given = dict(overrides, api_user=api_user, api_key=api_key, client_ip=client_ip)
        changes = {k: v for k, v in given.items() if v is not None}
        if settings is None:
            settings = load_settings(config_file, **changes)
        elif changes:
            settings = load_settings(None, **{**settings.model_dump(), **changes})

        self.settings = settings
        self._credentials = settings.require_credentials()
        self.base_url = settings.resolved_base_url()
        self.environment = settings.environment.lower()
        self.timeout = settings.timeout
        self.max_retries = settings.max_retries
        self.max_retry_wait = settings.max_retry_wait
        self.user_agent = settings.resolved_user_agent()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(environment={self.environment!r}, base_url={self.base_url!r})"

    def _headers(self) -> dict[str, str]:
        return {"Accept": "application/xml", "User-Agent": self.user_agent}

    def _request_args(self, call: Call) -> dict[str, Any]:
        params = {**self._credentials, "Command": call.command, **call.clean_params()}
        return {"data": params} if call.write else {"params": params}

    def _wait_for(self, attempt: int, retry_after: Optional[float] = None) -> float:
        if retry_after is not None:
            return max(0.0, retry_after)
        delay = self.settings.backoff_base * (2 ** attempt)
        return min(self.settings.backoff_cap, delay) + random.uniform(0, self.settings.backoff_base / 2)

    def _outcome(self, call: Call, response: httpx.Response) -> Any:
        if response.status_code != 200:
            raise from_status(response, call.command)
        root = parse_xml(response.text)
        if root.get("Status", "").upper() == "ERROR":
            details = [APIErrorDetail(e.get("Number", ""), (e.text or "").strip())
                       for e in root.iterfind("./Errors/Error")]
            raise from_details(details, call.command, response)
        found = root.find("CommandResponse")
        return call.parse(found if found is not None else root)

    def _retry_wait(self, error: Exception, attempt: int) -> Optional[float]:
        if attempt >= self.max_retries:
            return None
        if isinstance(error, RateLimitError):
            wait = self._wait_for(attempt, error.retry_after)
            return wait if wait <= self.max_retry_wait else None
        if isinstance(error, (ServerError, APIConnectionError)):
            return self._wait_for(attempt)
        return None

    def _execute(self, call: Call) -> Any:
        raise NotImplementedError

    def _drive(self, flow: Flow[Any]) -> Any:
        raise NotImplementedError


class SyncClient(BaseClient):
    def __init__(self, *args: Any, http_client: Optional[httpx.Client] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._owns_http = http_client is None
        self._http = http_client or httpx.Client(timeout=self.timeout)

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self: T) -> T:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _send(self, call: Call) -> httpx.Response:
        method = "POST" if call.write else "GET"
        try:
            return self._http.request(method, self.base_url, headers=self._headers(), **self._request_args(call))
        except httpx.TimeoutException as exc:
            raise APITimeoutError(text("error.timeout", error=exc)) from exc
        except httpx.TransportError as exc:
            raise APIConnectionError(text("error.connection", error=exc)) from exc

    def _execute(self, call: Call) -> Any:
        attempt = 0
        while True:
            try:
                return self._outcome(call, self._send(call))
            except (APIError, APIConnectionError) as error:
                wait = self._retry_wait(error, attempt)
                if wait is None:
                    raise
                time.sleep(wait)
                attempt += 1

    def _drive(self, flow: Flow[Any]) -> Any:
        try:
            call = next(flow)
            while True:
                call = flow.send(self._execute(call))
        except StopIteration as stop:
            return stop.value


class AsyncClient(BaseClient):
    def __init__(self, *args: Any, http_client: Optional[httpx.AsyncClient] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._owns_http = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=self.timeout)

    async def close(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self: T) -> T:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def _send(self, call: Call) -> httpx.Response:
        method = "POST" if call.write else "GET"
        try:
            return await self._http.request(method, self.base_url, headers=self._headers(),
                                            **self._request_args(call))
        except httpx.TimeoutException as exc:
            raise APITimeoutError(text("error.timeout", error=exc)) from exc
        except httpx.TransportError as exc:
            raise APIConnectionError(text("error.connection", error=exc)) from exc

    async def _execute(self, call: Call) -> Any:
        attempt = 0
        while True:
            try:
                return self._outcome(call, await self._send(call))
            except (APIError, APIConnectionError) as error:
                wait = self._retry_wait(error, attempt)
                if wait is None:
                    raise
                await asyncio.sleep(wait)
                attempt += 1

    async def _drive(self, flow: Flow[Any]) -> Any:
        try:
            call = next(flow)
            while True:
                call = flow.send(await self._execute(call))
        except StopIteration as stop:
            return stop.value


__all__ = ["Call", "Flow", "SyncClient", "AsyncClient", "parse_xml"]
