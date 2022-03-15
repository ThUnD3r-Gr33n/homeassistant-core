"""Enum backports from standard lib."""
from __future__ import annotations

from enum import Enum
from typing import Any, TypeVar

_T = TypeVar("_T", bound="StrEnum")


class StrEnum(str, Enum):
    """Partial backport of Python 3.11's StrEnum for our basic use cases."""

    def __new__(cls: type[_T], value: str, *args: Any, **kwargs: Any) -> _T:
        """Create a new StrEnum instance."""
        if not isinstance(value, str):
            raise TypeError(f"{value!r} is not a string")
        return super().__new__(cls, value, *args, **kwargs)

    def __str__(self) -> str:
        """Return self.value."""
        return str(self.value)

    @staticmethod
    def _generate_next_value_(  # pylint: disable=arguments-differ # https://github.com/PyCQA/pylint/issues/5371
        name: str, start: int, count: int, last_values: list[Any]
    ) -> Any:
        """
        Make `auto()` explicitly unsupported.

        We may revisit this when it's very clear that Python 3.11's
        `StrEnum.auto()` behavior will no longer change.
        """
        raise TypeError("auto() is not supported by this implementation")
