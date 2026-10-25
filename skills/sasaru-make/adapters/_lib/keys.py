from __future__ import annotations

import os

from .errors import InputError

_loaded: set[str] = set()


class Secret:
    """An API key read from the environment. Never formats as its value."""

    __slots__ = ("env", "_value")

    def __init__(self, env: str, value: str) -> None:
        self.env = env
        self._value = value

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"Secret({self.env}=***)"

    __str__ = __repr__

    def __format__(self, spec: str) -> str:
        return repr(self)


def read(*env_names: str) -> Secret:
    for name in env_names:
        value = os.environ.get(name, "").strip()
        if value:
            _loaded.add(value)
            return Secret(name, value)
    raise InputError(f"鍵の環境変数がありません: {' か '.join(env_names)}")


def redact(text: str) -> str:
    for value in _loaded:
        if value:
            text = text.replace(value, "***")
    return text
