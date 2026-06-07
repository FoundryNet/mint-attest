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

## Links

- Explorer: https://mint.foundrynet.io
- MCP server: https://github.com/FoundryNet/mint-mcp
- Protocol: https://foundrynet.io

MIT licensed.
