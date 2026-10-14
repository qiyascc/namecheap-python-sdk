from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import httpx


@dataclass(frozen=True)
class APIErrorDetail:
    number: str
    message: str


class NamecheapError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        number: Optional[str] = None,
        errors: Optional[list[APIErrorDetail]] = None,
        command: Optional[str] = None,
        response: Optional[httpx.Response] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.number = number
        self.errors = errors or []
        self.command = command
        self.response = response

    def __str__(self) -> str:
        parts = []
        if self.status_code and self.status_code != 200:
            parts.append(f"[{self.status_code}]")
        if self.number:
            parts.append(self.number)
        parts.append(self.message)
        if self.command:
            parts.append(f"({self.command})")
        return " ".join(parts)


class APIConnectionError(NamecheapError):
    pass


class APITimeoutError(APIConnectionError):
    pass


class APIError(NamecheapError):
    pass


class ValidationError(APIError):
    pass


class AuthenticationError(APIError):
    pass


class PermissionDeniedError(APIError):
    pass


class NotFoundError(APIError):
    pass


class RateLimitError(APIError):
    def __init__(self, message: str, *, retry_after: Optional[float] = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ServerError(APIError):
    pass


AUTH_NUMBERS = frozenset({
    "1010101", "1010102", "1011102", "1010104", "1010105", "1011105", "1030408", "1050900", "1011150",
    "1017150", "1017105", "1017101", "1017410", "1017411", "1019103", "1016103", "1017103",
})
NOT_FOUND_NUMBERS = frozenset({"2019166", "2016166"})
PERMISSION_NUMBERS = frozenset({"2030166", "4011103"})
VALIDATION_NUMBERS = frozenset({"3013288", "4013288", "2015278", "3011288"})
SERVER_NUMBERS = frozenset({"3031510", "3050900", "5050900", "5019169", "5050169", "4022288", "4023330"})
STATUS_MAP: dict[int, type[APIError]] = {401: AuthenticationError, 403: PermissionDeniedError, 404: NotFoundError}


def error_class(number: str, message: str) -> type[APIError]:
    lowered = message.lower()
    if "too many requests" in lowered or "rate limit" in lowered:
        return RateLimitError
    if number in AUTH_NUMBERS:
        return AuthenticationError
    if number in NOT_FOUND_NUMBERS:
        return NotFoundError
    if number in PERMISSION_NUMBERS:
        return PermissionDeniedError
    if number in VALIDATION_NUMBERS:
        return ValidationError
    if number in SERVER_NUMBERS or number.startswith("5"):
        return ServerError
    if number.startswith("2"):
        return ValidationError
    return APIError


def from_details(details: list[APIErrorDetail], command: str, response: Optional[httpx.Response] = None) -> APIError:
    first = details[0] if details else APIErrorDetail("", "")
    cls = error_class(first.number, first.message)
    message = "; ".join(d.message for d in details if d.message) or first.message
    return cls(message, number=first.number or None, errors=details, command=command,
               status_code=response.status_code if response is not None else None, response=response)


def from_status(response: httpx.Response, command: str) -> APIError:
    status = response.status_code
    message = response.reason_phrase or response.text.strip()[:200]
    if status == 429:
        header = response.headers.get("Retry-After")
        try:
            wait = float(header) if header else None
        except ValueError:
            wait = None
        return RateLimitError(message, retry_after=wait, status_code=status, command=command, response=response)
    cls = ServerError if status >= 500 else STATUS_MAP.get(status, APIError)
    return cls(message, status_code=status, command=command, response=response)
