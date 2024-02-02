"""Helpers to redact Google Assistant data when logging."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, TypeVar, cast, overload

from homeassistant.core import callback

REDACTED = "**REDACTED**"

_T = TypeVar("_T")
_ValueT = TypeVar("_ValueT")


def partial_redact(x: str, unmasked_prefix=4, unmasked_suffix=4) -> str:
    """Mask part of a string with *."""
    if not isinstance(x, str):
        return REDACTED

    unmasked = unmasked_prefix + unmasked_suffix
    if len(x) < unmasked * 2:
        return REDACTED

    return f"{x[:unmasked_prefix]}{'*' * (len(x) - unmasked)}{x[-unmasked_suffix:]}"


SYNC_MSG_TO_REDACT: dict[str, Callable[[str], str]] = {
    "agentUserId": partial_redact,
    "uuid": partial_redact,
    "webhookId": partial_redact,
}


@overload
def async_redact_data(  # type: ignore[overload-overlap]
    data: Mapping, to_redact: dict[Any, Callable[[_ValueT], _ValueT]]
) -> dict:
    ...


@overload
def async_redact_data(
    data: _T, to_redact: dict[Any, Callable[[_ValueT], _ValueT]]
) -> _T:
    ...


@callback
def async_redact_data(
    data: _T, to_redact: dict[Any, Callable[[_ValueT], _ValueT]]
) -> _T:
    """Redact sensitive data in a dict."""
    if not isinstance(data, (Mapping, list)):
        return data

    if isinstance(data, list):
        return cast(_T, [async_redact_data(val, to_redact) for val in data])

    redacted = {**data}

    for key, value in redacted.items():
        if value is None:
            continue
        if isinstance(value, str) and not value:
            continue
        if key in to_redact:
            redacted[key] = to_redact[key](value)
        elif isinstance(value, Mapping):
            redacted[key] = async_redact_data(value, to_redact)
        elif isinstance(value, list):
            redacted[key] = [async_redact_data(item, to_redact) for item in value]

    return cast(_T, redacted)


@callback
def async_redact_sync(msg: dict[str, Any]) -> dict[str, Any]:
    """Mask sensitive data in sync message."""
    return async_redact_data(msg, SYNC_MSG_TO_REDACT)
