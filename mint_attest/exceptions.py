"""Exceptions for the mint-attest SDK.

All inherit from MintError so callers can `except MintError` to catch everything.
The @attest decorator swallows MintError by default (attestation must never break
the wrapped function); the explicit MintClient methods raise so callers can handle.
"""
from __future__ import annotations

from typing import Any, Optional


class MintError(Exception):
    """Base class for all mint-attest errors."""


class MintAuthError(MintError):
    """No API key configured, or the server rejected it."""


class MintConfigError(MintError):
    """The client is missing required configuration (e.g. an agent name)."""


class MintAPIError(MintError):
    """The MINT API returned an error or was unreachable."""

    def __init__(self, message: str, *, status: Optional[int] = None,
                 detail: Any = None):
        super().__init__(message)
        self.status = status
        self.detail = detail
