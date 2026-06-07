"""MintClient — the core: register, attest, verify against the MINT REST surface.

Talks plain HTTPS to the MINT server (default mint-mcp); the server handles all
Solana interaction. The developer never touches a wallet, signs a transaction, or
imports a blockchain library — it's just an API call. The developer's fnet_ key
(arg or MINT_API_KEY env) authenticates every request, so the agent and its
attestations belong to their account.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from typing import Any, Optional

import httpx

from . import __version__
from .exceptions import MintAPIError, MintAuthError, MintConfigError
from .models import Actor, Receipt, TrustScore

DEFAULT_ENDPOINT = "https://mint-mcp-production.up.railway.app"


def hash_data(obj: Any) -> str:
    """Deterministic SHA-256 of any value. bytes as-is, str as utf-8, everything
    else as canonical (sorted-key) JSON so the same input always hashes the same."""
    if isinstance(obj, (bytes, bytearray)):
        b = bytes(obj)
    elif isinstance(obj, str):
        b = obj.encode("utf-8")
    else:
        b = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def _strip_none(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


class MintClient:
    """One client per agent process. Register once (or let attest auto-register),
    then attest each unit of work."""

    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None,
                 *, name: Optional[str] = None, actor_type: str = "ai_agent",
                 capabilities: Optional[list] = None, operator: Optional[str] = None,
                 timeout: float = 30.0, transport: Optional[httpx.BaseTransport] = None):
        self.api_key = api_key or os.environ.get("MINT_API_KEY")
        self.endpoint = (endpoint or os.environ.get("MINT_ENDPOINT") or DEFAULT_ENDPOINT).rstrip("/")
        self.timeout = timeout
        # defaults used by auto-register; name also fills from MINT_AGENT_NAME
        self._name = name or os.environ.get("MINT_AGENT_NAME")
        self._actor_type = actor_type
        self._capabilities = capabilities
        self._operator = operator or os.environ.get("MINT_OPERATOR")
        self._actor: Optional[Actor] = None
        self._http = httpx.Client(timeout=timeout, transport=transport)

    # ── identity helpers ──────────────────────────────────────────────────────
    @property
    def mint_id(self) -> Optional[str]:
        return self._actor.mint_id if self._actor else None

    @property
    def actor(self) -> Optional[Actor]:
        return self._actor

    def _headers(self) -> dict:
        if not self.api_key:
            raise MintAuthError(
                "No API key. Pass MintClient(api_key='fnet_…') or set MINT_API_KEY.")
        return {"Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": f"mint-attest/{__version__}"}

    def _post(self, path: str, body: dict) -> dict:
        try:
            r = self._http.post(self.endpoint + path, json=body, headers=self._headers())
        except httpx.HTTPError as e:
            raise MintAPIError(f"network error calling {path}: {e}") from e
        try:
            data = r.json()
        except Exception:
            raise MintAPIError(f"non-JSON response from {path} (HTTP {r.status_code})",
                               status=r.status_code, detail=r.text[:300])
        if r.status_code >= 400 or (isinstance(data, dict) and data.get("error")):
            detail = data.get("detail") if isinstance(data, dict) else data
            code = data.get("error") if isinstance(data, dict) else f"http_{r.status_code}"
            if r.status_code in (401, 403):
                raise MintAuthError(f"{code}: {detail}")
            raise MintAPIError(f"{code}: {detail}", status=r.status_code, detail=detail)
        return data

    # ── register ──────────────────────────────────────────────────────────────
    def register(self, name: Optional[str] = None, actor_type: Optional[str] = None,
                 capabilities: Optional[list] = None, operator: Optional[str] = None,
                 metadata: Optional[dict] = None) -> Actor:
        """Provision (or look up — idempotent) this agent's MINT identity. Caches
        the mint_id so later attest() calls reuse it. FREE."""
        resolved_name = name or self._name
        if not resolved_name:
            raise MintConfigError(
                "An agent name is required to register. Pass name=… (or set "
                "MINT_AGENT_NAME / use @attest, which names the agent after the function).")
        body = _strip_none({
            "name": resolved_name,
            "actor_type": actor_type or self._actor_type,
            "capabilities": capabilities if capabilities is not None else self._capabilities,
            "operator": operator or self._operator,
            "metadata": metadata,
        })
        actor = Actor.from_dict(self._post("/v1/register", body))
        self._actor = actor
        # remember resolved defaults for any future auto-register
        self._name = self._name or resolved_name
        return actor

    def _ensure_actor(self) -> Actor:
        if self._actor is None:
            self.register()
        return self._actor  # type: ignore[return-value]

    # ── attest ─────────────────────────────────────────────────────────────────
    def attest(self, work_type: str, input_data: Any = None, output_data: Any = None,
               duration_seconds: Optional[float] = None, summary: Optional[str] = None,
               metadata: Optional[dict] = None, *, mint_id: Optional[str] = None,
               input_hash: Optional[str] = None, output_hash: Optional[str] = None) -> Receipt:
        """Attest a completed unit of work — anchors a tamper-evident record on
        Solana mainnet and returns a Receipt (with verify_url). 2¢ per attestation.

        Pass input_data/output_data (any value — hashed for you) OR precomputed
        input_hash/output_hash. Auto-registers the agent on the first call if it
        hasn't been registered yet.
        """
        mid = mint_id or self.mint_id or self._ensure_actor().mint_id
        if input_hash is None and input_data is not None:
            input_hash = hash_data(input_data)
        if output_hash is None and output_data is not None:
            output_hash = hash_data(output_data)
        # Forge requires duration_seconds > 0; round sub-second work up to 1.
        dur = max(1, int(math.ceil(duration_seconds))) if duration_seconds else 1
        body = _strip_none({
            "mint_id": mid, "work_type": work_type, "duration_seconds": dur,
            "summary": summary or f"{work_type} completed",
            "input_hash": input_hash, "output_hash": output_hash, "metadata": metadata,
        })
        return Receipt.from_dict(self._post("/v1/attest", body))

    # ── verify ──────────────────────────────────────────────────────────────────
    def verify(self, mint_id: Optional[str] = None, actor_name: Optional[str] = None,
               actor_type: Optional[str] = None) -> TrustScore:
        """Look up any actor's trust profile. FREE. Defaults to this client's own
        agent when no identifier is given."""
        body = _strip_none({
            "mint_id": mint_id or (None if actor_name else self.mint_id),
            "actor_name": actor_name, "actor_type": actor_type,
        })
        if not body:
            raise MintConfigError("Provide mint_id or actor_name (or register first).")
        return TrustScore.from_dict(self._post("/v1/verify", body))

    # ── lifecycle ────────────────────────────────────────────────────────────────
    def close(self) -> None:
        try:
            self._http.close()
        except Exception:
            pass

    def __enter__(self) -> "MintClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
