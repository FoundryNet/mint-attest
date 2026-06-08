"""Typed return values: Actor, Receipt, TrustScore.

Each `.from_dict` is tolerant of extra/missing fields (the server may add fields
over time) and keeps the full payload on `.raw` so nothing is ever lost.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Actor:
    """A registered MINT identity."""
    mint_id: Optional[str]
    name: Optional[str] = None
    actor_type: Optional[str] = None
    capabilities: list = field(default_factory=list)
    operator: Optional[str] = None
    wallet_address: Optional[str] = None
    newly_registered: bool = False
    # Set only on autonomous (keyless) registration: the freshly minted fnet_ key,
    # scoped to this actor. Returned ONCE — persist it. None on a keyed register.
    api_key: Optional[str] = None
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Actor":
        return cls(
            mint_id=d.get("mint_id"),
            name=d.get("name"),
            actor_type=d.get("actor_type"),
            capabilities=d.get("capabilities") or [],
            operator=d.get("operator"),
            wallet_address=d.get("wallet_address"),
            newly_registered=bool(d.get("newly_registered") or d.get("autonomous")),
            api_key=d.get("api_key"),
            raw=d,
        )


@dataclass
class Receipt:
    """The result of an attestation — the proof your agent did the work."""
    attestation_id: Optional[str]
    mint_id: Optional[str]
    work_type: Optional[str] = None
    data_hash: Optional[str] = None
    tx_signature: Optional[str] = None
    verify_url: Optional[str] = None
    trust_score: Optional[Any] = None
    reward: Optional[Any] = None
    settled: bool = False
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Receipt":
        return cls(
            attestation_id=d.get("attestation_id"),
            mint_id=d.get("mint_id"),
            work_type=d.get("work_type"),
            data_hash=d.get("data_hash"),
            tx_signature=d.get("tx_signature"),
            verify_url=d.get("verify_url"),
            trust_score=d.get("trust_score"),
            reward=d.get("reward"),
            settled=bool(d.get("settled")),
            raw=d,
        )

    def __str__(self) -> str:
        return f"<Receipt {self.attestation_id} settled={self.settled} verify={self.verify_url}>"


@dataclass
class TrustScore:
    """An actor's reputation. `score`/`total_attestations` are None while the
    on-chain trust-read endpoint is rolling out; `pending` is True in that case."""
    mint_id: Optional[str]
    score: Optional[float] = None
    total_attestations: Optional[int] = None
    pending: bool = False
    registered: bool = False
    name: Optional[str] = None
    actor_type: Optional[str] = None
    work_types: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)

    @staticmethod
    def _num(v):
        # the server uses the sentinel string "pending" until trust-read ships
        if isinstance(v, (int, float)):
            return v, False
        if v == "pending":
            return None, True
        return None, False

    @classmethod
    def from_dict(cls, d: dict) -> "TrustScore":
        score, p1 = cls._num(d.get("trust_score"))
        total, p2 = cls._num(d.get("total_attestations"))
        return cls(
            mint_id=d.get("mint_id"),
            score=score,
            total_attestations=int(total) if total is not None else None,
            pending=bool(p1 or p2 or d.get("trust_read_status") == "pending_forge_endpoint"),
            registered=bool(d.get("registered")),
            name=d.get("name"),
            actor_type=d.get("actor_type"),
            work_types=d.get("work_types") or {},
            raw=d,
        )
