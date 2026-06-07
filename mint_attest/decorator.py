"""@attest — zero-friction attestation for any Python function, plus the
process-wide default client.

    from mint_attest import attest

    @attest(work_type="code_review")
    def review_code(files):
        return do_the_review(files)

Every call hashes the inputs/output, times the call, attests on MINT, and returns
the function's result UNCHANGED. Attestation failures (no key, network blip) are
logged and swallowed by default — instrumentation must never break the agent.
Set strict=True to raise instead.
"""
from __future__ import annotations

import logging
import math
import time
from functools import wraps
from typing import Callable, Optional

from .client import MintClient, hash_data
from .exceptions import MintError

log = logging.getLogger("mint_attest")

_default_client: Optional[MintClient] = None


def get_default_client() -> MintClient:
    """The lazily-created process-wide client (uses MINT_API_KEY / env defaults)."""
    global _default_client
    if _default_client is None:
        _default_client = MintClient()
    return _default_client


def set_default_client(client: MintClient) -> None:
    """Override the process-wide client (e.g. with a custom endpoint or key)."""
    global _default_client
    _default_client = client


def configure(api_key: Optional[str] = None, endpoint: Optional[str] = None,
              name: Optional[str] = None, actor_type: str = "ai_agent",
              capabilities: Optional[list] = None, operator: Optional[str] = None) -> MintClient:
    """Set up the default client in one call. Optional — env vars work too."""
    client = MintClient(api_key=api_key, endpoint=endpoint, name=name,
                        actor_type=actor_type, capabilities=capabilities, operator=operator)
    set_default_client(client)
    return client


def attest(work_type: str, name: Optional[str] = None,
           capabilities: Optional[list] = None, client: Optional[MintClient] = None,
           strict: bool = False) -> Callable:
    """Decorator: attest every call of the wrapped function on MINT.

    Args:
        work_type: code_review|research|generation|analysis|delivery|
            normalization|manufacturing|custom.
        name: agent name to register under (defaults to the function's name; set
            once for the process).
        capabilities: capability tags recorded at registration.
        client: a specific MintClient (defaults to the process-wide one).
        strict: if True, re-raise attestation errors instead of swallowing them.
    """
    def wrapper(func: Callable) -> Callable:
        @wraps(func)
        def inner(*args, **kwargs):
            c = client or get_default_client()
            # name the agent once: explicit name > whatever's already set > func name
            if not c._name:
                c._name = name or func.__name__
            if capabilities and c._capabilities is None:
                c._capabilities = capabilities

            start = time.time()
            result = func(*args, **kwargs)          # run the real work first
            duration = max(1, int(math.ceil(time.time() - start)))

            try:
                c.attest(
                    work_type=work_type,
                    input_hash=hash_data({"args": args, "kwargs": kwargs}),
                    output_hash=hash_data(result),
                    duration_seconds=duration,
                    summary=f"{func.__name__} completed",
                )
            except MintError as e:
                if strict:
                    raise
                log.warning("mint-attest: attestation skipped (%s) — returning result anyway", e)
            return result
        return inner
    return wrapper
