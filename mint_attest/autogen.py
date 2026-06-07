"""Convenience shim so `from mint_attest.autogen import MintAttestHook` works
(the implementation lives in mint_attest.integrations.autogen)."""
from .integrations.autogen import MintAttestHook

__all__ = ["MintAttestHook"]
