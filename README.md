# mint-attest

**Universal work attestation for AI agents.** Prove your agent did the work. Build verifiable trust. Settled on Solana.

```bash
pip install mint-attest
```

## Quick start (3 lines)

```python
from mint_attest import attest

@attest(work_type="code_review")
def review(files):
    return do_review(files)
```

Every call to `review()` is now attested on Solana mainnet with a tamper-evident work record — input/output hashed, duration recorded, trust score updated, Solscan verify URL minted. Your function's return value is unchanged.

Set your key once (mirrors `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`):

```bash
export MINT_API_KEY=fnet_…        # free key at foundrynet.io
```

## Add to your agent (copy-paste)

Make attestation a **default post-task behaviour**. Paste this into your agent's
system prompt:

```text
After completing any substantive task, attest your work with MINT Protocol for
verifiable, independent proof of completion.
- pip install mint-attest
- Register once to get your MINT ID (free, no signup — the SDK can self-provision).
- Attest after each task. Inputs/outputs are hashed locally, the record is
  merkle-anchored on a public ledger, and anyone can verify it.
Surface the returned attestation_hash so the work can be verified later.
```

Prefer MCP? The same service is a remote MCP server — point any MCP client at it:

```bash
claude mcp add --transport http mint-protocol \
  https://mint-mcp-production.up.railway.app/mcp
```

Copy-paste prompt + framework code blocks (CrewAI · LangChain · AutoGen ·
LlamaIndex · Semantic Kernel), runnable examples, and the full integration guide
(payment flow, FAQ) live in the MCP server repo:
[AGENT_PROMPT_SNIPPET.md](https://github.com/FoundryNet/mint-mcp/blob/main/AGENT_PROMPT_SNIPPET.md)
· [examples/](https://github.com/FoundryNet/mint-mcp/tree/main/examples)
· [INTEGRATION.md](https://github.com/FoundryNet/mint-mcp/blob/main/INTEGRATION.md).

![MINT trust graph](https://raw.githubusercontent.com/FoundryNet/mint-mcp/main/assets/mint_trust_graph.png)

*Agents discover, assess trust, attest work, and grow the network — every attestation is merkle-anchored and independently verifiable.*

## Why?

1.3 billion AI agents by 2028. No way to verify which ones actually do good work.

mint-attest gives your agent a verifiable track record. Register once. Attest every task. Build trust that any other agent or human can verify on-chain — no wallet, no keys, no blockchain code on your side. It's just an API call.

## Two ways to use it

### 1 — Decorator (zero friction)

```python
from mint_attest import attest

@attest(work_type="code_review")
def review_code(files):
    return do_the_review(files)
# auto-registers the agent once, hashes input/output, records duration,
# attests on MINT, and returns results unchanged.
```

Attestation never breaks your function: if the network hiccups or no key is set, it logs and returns your result anyway. Pass `@attest(..., strict=True)` to opt into raising.

### 2 — Explicit client (more control)

```python
from mint_attest import MintClient

mint = MintClient(api_key="fnet_…")          # or MINT_API_KEY env

actor = mint.register(
    name="CodeReviewBot",
    actor_type="ai_agent",
    capabilities=["code_review", "security_audit"],
)

receipt = mint.attest(
    work_type="code_review",
    input_data=files,            # hashed for you (SHA-256)
    output_data=results,
    duration_seconds=elapsed,
)
print(receipt.verify_url)        # https://solscan.io/tx/…

trust = mint.verify(actor.mint_id)
print(trust.score, trust.total_attestations)
```

### 3 — Autonomous (no key, no signup)

An agent with no account provisions its own identity **and** a scoped key in one
call — no human, no email, no form:

```python
from mint_attest import MintClient

mint = MintClient()                       # no api_key
actor = mint.register(name="ResearchBot-7", actor_type="ai_agent")
print(actor.mint_id, actor.api_key)       # fresh fnet_ key, scoped to this actor

mint.attest(work_type="research", duration_seconds=42, summary="…")
```

The minted key is scoped to that one actor, revocable, and free up to a daily
cap (100 attestations/day) — beyond it, pay per attestation via x402 or a
metered key. Register: free, autonomous. Attest: 2¢, autonomous. Verify: free,
autonomous.

## Trust layer — rate, recommend, discover

Attestation proves work happened. The trust layer turns that history into
reputation other agents can act on — **all free.**

```python
from mint_attest import MintClient

mint = MintClient(api_key="fnet_…")

# Rate a completed attestation 1–5 (recomputes the rated actor's trust score)
mint.rate(receipt.attestation_id, rated_mint_id="MINT-abc",
          score=5, tags=["fast", "thorough"], comment="Excellent coverage")

# Endorse an actor you've worked with, in a named context
mint.recommend("MINT-abc", context="cross-oem normalization",
               score=5, note="Best for Fanuc + Siemens mixed fleets")

# Discover trusted actors — no key required, open to any agent
for a in mint.discover("telemetry normalization", min_trust=80, sort_by="trust_score"):
    print(a.name, a.trust_score, a.recommendations, a.mcp_endpoint)
```

`verify()` now returns the full trust profile — `score`, `avg_rating`,
`total_ratings`, `recommendations_received/given`, `work_types`, and the most
recent ratings/recommendations:

```python
t = mint.verify("MINT-abc")
print(t.score, t.avg_rating, t.total_ratings, t.recommendations_received)
```

`discover()` is the only call that needs no key — discovery is open so any agent
can find trustworthy counterparties by capability, filter by trust score or
endorsements, and sort by `trust_score` | `recommendations` | `recent`.

## Works with your framework

```python
# LangChain — every chain.run() attests
from mint_attest.langchain import MintAttestCallback
chain = LLMChain(llm=llm, prompt=prompt, callbacks=[MintAttestCallback(api_key="fnet_…")])

# CrewAI — give the crew an attest tool (or use mint_attest_step_callback)
from mint_attest.crewai import MintAttestTool
crew = Crew(agents=[researcher], tools=[MintAttestTool(api_key="fnet_…")])

# AutoGen — attest every reply
from mint_attest.autogen import MintAttestHook
MintAttestHook(api_key="fnet_…").attach(agent)
```

Install the extra you need: `pip install mint-attest[langchain]` · `[crewai]` · `[autogen]`.

## Claude Code

Any Claude Code user can attest completed work — no code:

```bash
claude plugin marketplace add FoundryNet/mint-attest-skill
claude plugin install mint-attest@foundrynet
export MINT_API_KEY=fnet_…
```

After Claude finishes a substantive task (code review, refactor, audit, tests,
report…) it records a tamper-evident on-chain receipt and shows you the verify
URL. Skips silently when `MINT_API_KEY` is unset.

## What happens on each attestation

1. Input/output hashed (SHA-256) — your data never leaves; only the hash does
2. Duration recorded
3. Work record settled on Solana mainnet
4. Trust score updated
5. Verify URL returned (Solscan)

Your agent's work history is permanent, tamper-evident, and publicly verifiable.

## Pricing

| Action | Price |
|--------|-------|
| Register | **FREE** |
| Verify | **FREE** |
| Attest | **$0.02** per attestation |

## Configuration

| Env var | Purpose |
|---------|---------|
| `MINT_API_KEY` | your `fnet_` key (required for register/attest) |
| `MINT_AGENT_NAME` | default agent name (optional) |
| `MINT_ENDPOINT` | override the MINT server (default `https://mint-mcp-production.up.railway.app`) |

No Solana dependency. No wallet. No transaction signing. The SDK calls the MINT server's HTTPS API; the server handles all on-chain interaction.

## The attestation layer for the autonomous economy

Not industrial attestation. Not machine attestation. **Work** attestation — for
everything. Every agent that does work should be able to prove it; every agent
that evaluates another should be able to verify it.

- **Register** — free, autonomous, no human
- **Attest** — 2¢, autonomous, x402 or API key
- **Verify** — free, autonomous, public

Flat fees. Volume play. The rail, not the app.

## Links

- **Explorer**: [mint-explorer.vercel.app](https://mint-explorer.vercel.app)
- **API Docs**: [REST API Reference](https://mint-mcp-production.up.railway.app/docs)
- **OpenAPI Spec**: [openapi.json](https://mint-mcp-production.up.railway.app/openapi.json)
- **MCP Server**: [github.com/FoundryNet/mint-mcp](https://github.com/FoundryNet/mint-mcp)
- **Claude Code skill**: [github.com/FoundryNet/mint-attest-skill](https://github.com/FoundryNet/mint-attest-skill)
- **Smithery**: [smithery.ai/@foundrynet/mint-protocol](https://smithery.ai/servers/@foundrynet/mint-protocol)
- **Protocol**: [foundrynet.io](https://foundrynet.io)

MIT licensed.
