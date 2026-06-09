"""Typed return values: Actor, Receipt, TrustScore, Rating, Recommendation,
Discovered.

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
    """An actor's reputation. The trust layer is live: `score` is the 0–100 trust
    score and the rating/recommendation fields are populated. `pending` is True
    only on older servers where the on-chain trust-read endpoint hadn't shipped."""
    mint_id: Optional[str]
    score: Optional[float] = None
    total_attestations: Optional[int] = None
    pending: bool = False
    registered: bool = False
    name: Optional[str] = None
    actor_type: Optional[str] = None
    work_types: dict = field(default_factory=dict)
    avg_rating: Optional[float] = None
    total_ratings: int = 0
    recommendations_received: int = 0
    recommendations_given: int = 0
    last_active: Optional[str] = None
    recent_ratings: list = field(default_factory=list)
    recent_recommendations: list = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    @staticmethod
    def _num(v):
        # older servers used the sentinel string "pending" before trust-read shipped
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
            avg_rating=d.get("avg_rating"),
            total_ratings=int(d.get("total_ratings") or 0),
            recommendations_received=int(d.get("recommendations_received") or 0),
            recommendations_given=int(d.get("recommendations_given") or 0),
            last_active=d.get("last_active"),
            recent_ratings=d.get("recent_ratings") or [],
            recent_recommendations=d.get("recent_recommendations") or [],
            raw=d,
        )


@dataclass
class Rating:
    """The result of rating an attestation."""
    rating_id: Optional[str]
    attestation_id: Optional[str] = None
    rated_mint_id: Optional[str] = None
    rater_mint_id: Optional[str] = None
    score: Optional[int] = None
    data_hash: Optional[str] = None
    trust_score_updated: Optional[float] = None
    status: Optional[str] = None
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Rating":
        return cls(
            rating_id=d.get("rating_id"), attestation_id=d.get("attestation_id"),
            rated_mint_id=d.get("rated_mint_id"), rater_mint_id=d.get("rater_mint_id"),
            score=d.get("score"), data_hash=d.get("data_hash"),
            trust_score_updated=d.get("trust_score_updated"), status=d.get("status"), raw=d)


@dataclass
class Recommendation:
    """The result of recommending an actor."""
    recommendation_id: Optional[str]
    recommended_mint_id: Optional[str] = None
    recommender_mint_id: Optional[str] = None
    context: Optional[str] = None
    score: Optional[int] = None
    data_hash: Optional[str] = None
    trust_score_updated: Optional[float] = None
    status: Optional[str] = None
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Recommendation":
        return cls(
            recommendation_id=d.get("recommendation_id"),
            recommended_mint_id=d.get("recommended_mint_id"),
            recommender_mint_id=d.get("recommender_mint_id"),
            context=d.get("context"), score=d.get("score"), data_hash=d.get("data_hash"),
            trust_score_updated=d.get("trust_score_updated"), status=d.get("status"), raw=d)


@dataclass
class Discovered:
    """One actor returned by discover()."""
    mint_id: Optional[str]
    name: Optional[str] = None
    actor_type: Optional[str] = None
    trust_score: Optional[float] = None
    total_attestations: int = 0
    avg_rating: Optional[float] = None
    total_ratings: int = 0
    recommendations: int = 0
    capabilities: list = field(default_factory=list)
    mcp_endpoint: Optional[str] = None
    description: Optional[str] = None
    last_active: Optional[str] = None
    top_recommendations: list = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Discovered":
        return cls(
            mint_id=d.get("mint_id"), name=d.get("name"), actor_type=d.get("actor_type"),
            trust_score=d.get("trust_score"), total_attestations=int(d.get("total_attestations") or 0),
            avg_rating=d.get("avg_rating"), total_ratings=int(d.get("total_ratings") or 0),
            recommendations=int(d.get("recommendations") or 0),
            capabilities=d.get("capabilities") or [], mcp_endpoint=d.get("mcp_endpoint"),
            description=d.get("description"), last_active=d.get("last_active"),
            top_recommendations=d.get("top_recommendations") or [], raw=d)
