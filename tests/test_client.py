"""Tests for mint-attest — run with `pytest` or `python tests/test_client.py`.

Uses an httpx MockTransport standing in for the MINT REST server, so the full
client/decorator/model contract is exercised with zero network.
"""
from __future__ import annotations

import json
import os
import sys

import httpx

# allow running directly without installing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mint_attest import (Actor, MintClient, Receipt, TrustScore, attest,  # noqa: E402
                         hash_data, set_default_client)
from mint_attest.exceptions import MintAPIError, MintAuthError  # noqa: E402


def make_transport(record, *, attest_error=False):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        body = json.loads(request.content or b"{}")
        record.setdefault("calls", []).append((path, body, dict(request.headers)))
        if path == "/v1/register":
            return httpx.Response(200, json={
                "mint_id": "MINT-test01", "name": body.get("name"),
                "actor_type": body.get("actor_type"),
                "capabilities": body.get("capabilities") or [],
                "newly_registered": True, "wallet_address": "WALLETxyz", "status": "active"})
        if path == "/v1/attest":
            if attest_error:
                return httpx.Response(502, json={"error": "attest_failed", "detail": "boom"})
            return httpx.Response(200, json={
                "attestation_id": "att-abc", "mint_id": body.get("mint_id"),
                "work_type": body.get("work_type"), "data_hash": "d" * 64,
                "tx_signature": "sig123", "verify_url": "https://solscan.io/tx/sig123",
                "trust_score": 100, "reward": 1.5, "settled": True})
        if path == "/v1/verify":
            return httpx.Response(200, json={
                "mint_id": body.get("mint_id") or "MINT-test01", "registered": True,
                "actor_type": "ai_agent", "name": "x", "trust_score": "pending",
                "total_attestations": "pending",
                "trust_read_status": "pending_forge_endpoint", "work_types": {}})
        return httpx.Response(404, json={"error": "not_found"})
    return httpx.MockTransport(handler)


def client(record, **kw):
    return MintClient(api_key="fnet_test", transport=make_transport(record, **kw), **kw_strip(kw))


def kw_strip(kw):  # don't pass attest_error into MintClient
    return {k: v for k, v in kw.items() if k not in ("attest_error",)}


# ── tests ─────────────────────────────────────────────────────────────────────
def test_register_returns_actor():
    rec = {}
    c = MintClient(api_key="fnet_test", transport=make_transport(rec))
    a = c.register(name="CodeReviewBot", capabilities=["code_review"])
    assert isinstance(a, Actor) and a.mint_id == "MINT-test01"
    assert c.mint_id == "MINT-test01"
    path, body, headers = rec["calls"][0]
    assert path == "/v1/register" and body["name"] == "CodeReviewBot"
    assert headers["authorization"] == "Bearer fnet_test"


def test_attest_hashes_and_returns_receipt():
    rec = {}
    c = MintClient(api_key="fnet_test", transport=make_transport(rec), name="bot")
    r = c.attest(work_type="code_review", input_data={"files": ["a.py"]},
                 output_data={"issues": 3}, duration_seconds=12)
    assert isinstance(r, Receipt) and r.verify_url == "https://solscan.io/tx/sig123"
    assert r.settled is True
    # auto-registered first, then attested
    assert [p for p, _, _ in rec["calls"]] == ["/v1/register", "/v1/attest"]
    _, body, _ = rec["calls"][1]
    assert body["input_hash"] == hash_data({"files": ["a.py"]})
    assert body["output_hash"] == hash_data({"issues": 3})
    assert body["duration_seconds"] == 12 and body["mint_id"] == "MINT-test01"


def test_attest_duration_min_one():
    rec = {}
    c = MintClient(api_key="fnet_test", transport=make_transport(rec), name="bot")
    c.attest(work_type="research", duration_seconds=0.2)   # sub-second → 1
    _, body, _ = rec["calls"][-1]
    assert body["duration_seconds"] == 1


def test_verify_pending():
    rec = {}
    c = MintClient(api_key="fnet_test", transport=make_transport(rec), name="bot")
    c.register()
    t = c.verify()
    assert isinstance(t, TrustScore) and t.pending is True
    assert t.score is None and t.total_attestations is None and t.registered is True


def test_missing_key_raises():
    os.environ.pop("MINT_API_KEY", None)
    c = MintClient(transport=make_transport({}), name="bot")
    try:
        c.register()
        assert False, "expected MintAuthError"
    except MintAuthError:
        pass


def test_decorator_returns_result_and_attests():
    rec = {}
    set_default_client(MintClient(api_key="fnet_test", transport=make_transport(rec)))

    @attest(work_type="code_review")
    def review(files):
        return {"reviewed": len(files)}

    out = review(["a.py", "b.py"])
    assert out == {"reviewed": 2}                       # result unchanged
    paths = [p for p, _, _ in rec["calls"]]
    assert paths == ["/v1/register", "/v1/attest"]
    # agent named after the function
    _, reg_body, _ = rec["calls"][0]
    assert reg_body["name"] == "review"


def test_decorator_auto_registers_once():
    rec = {}
    set_default_client(MintClient(api_key="fnet_test", transport=make_transport(rec)))

    @attest(work_type="research", name="multi")
    def work(x):
        return x * 2

    assert work(2) == 4 and work(3) == 6
    paths = [p for p, _, _ in rec["calls"]]
    assert paths.count("/v1/register") == 1            # registered once, cached
    assert paths.count("/v1/attest") == 2


def test_decorator_swallows_errors():
    rec = {}
    set_default_client(MintClient(api_key="fnet_test",
                                  transport=make_transport(rec, attest_error=True)))

    @attest(work_type="research")
    def work(x):
        return x + 1

    # attest fails (502) but the function result is returned anyway
    assert work(41) == 42


def test_explicit_attest_raises_on_error():
    c = MintClient(api_key="fnet_test", transport=make_transport({}, attest_error=True), name="bot")
    try:
        c.attest(work_type="research", duration_seconds=1)
        assert False, "expected MintAPIError"
    except MintAPIError as e:
        assert e.status == 502


def test_trustscore_numeric():
    t = TrustScore.from_dict({"mint_id": "MINT-x", "trust_score": 94,
                              "total_attestations": 47291, "registered": True})
    assert t.score == 94 and t.total_attestations == 47291 and t.pending is False


# ── runner ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
