"""mint-attest — universal work attestation for AI agents.

    from mint_attest import attest

    @attest(work_type="code_review")
    def review(files):
        return do_review(files)

Register once, attest every task, build a verifiable on-chain track record. The
SDK is a thin HTTPS client to the MINT server; all Solana interaction happens
server-side. Framework integrations live in mint_attest.langchain / .crewai /
.autogen (imported only when you use them).
"""
from __future__ import annotations

__version__ = "0.3.2"

from .client import MintClient, hash_data
from .decorator import attest, configure, get_default_client, set_default_client
from .exceptions import MintAPIError, MintAuthError, MintConfigError, MintError
from .models import Actor, Discovered, Rating, Receipt, Recommendation, TrustScore

__all__ = [
    "__version__",
    "attest", "configure", "MintClient",
    "get_default_client", "set_default_client", "hash_data",
    "Actor", "Receipt", "TrustScore", "Rating", "Recommendation", "Discovered",
    "MintError", "MintAuthError", "MintAPIError", "MintConfigError",
]
