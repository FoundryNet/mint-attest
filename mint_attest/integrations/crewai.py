"""CrewAI integration — give a crew a tool that attests completed work.

    from mint_attest.crewai import MintAttestTool

    crew = Crew(agents=[researcher], tools=[MintAttestTool(api_key="fnet_…")])

The agent calls `mint_attest` when it finishes a unit of work, passing a short
summary (and optionally the work_type); the tool anchors it on MINT and returns
the Solscan verify URL. For fully-automatic attestation of every task, also see
`mint_attest_step_callback` below, which you can pass as Crew(step_callback=…).
"""
from __future__ import annotations

import logging
import time
from typing import Optional, Type

from pydantic import BaseModel, Field

from ..client import MintClient
from ..exceptions import MintError

log = logging.getLogger("mint_attest.crewai")


def _base_tool():
    try:
        from crewai.tools import BaseTool          # crewai >= 0.x current
        return BaseTool
    except Exception:
        pass
    try:
        from crewai_tools import BaseTool          # alt package
        return BaseTool
    except Exception as e:
        raise ImportError(
            "CrewAI is not installed. `pip install mint-attest[crewai]` "
            "(or `pip install crewai`)."
        ) from e


_BaseTool = _base_tool()


class MintAttestToolSchema(BaseModel):
    """Arguments the agent passes when it attests a completed unit of work.

    Declared explicitly so the tool works across CrewAI versions — CrewAI 1.x
    otherwise tries to build this schema from `_run`'s annotations, which this module
    defers via `from __future__ import annotations`, and can't resolve on its own.
    """
    summary: str = Field(
        ..., description="What you did and the result (one or two sentences).")
    work_type: Optional[str] = Field(
        default=None,
        description="Optional work category: research | analysis | generation | "
                    "code_review | delivery | custom.")


class MintAttestTool(_BaseTool):  # type: ignore[misc,valid-type]
    name: str = "mint_attest"
    description: str = (
        "Attest a completed unit of work on the MINT network for a tamper-evident, "
        "on-chain record. Call after finishing a task. Args: summary (str, what you "
        "did and the result), work_type (str, optional: research|analysis|generation|"
        "code_review|delivery|custom).")
    args_schema: Type[BaseModel] = MintAttestToolSchema

    def __init__(self, api_key: Optional[str] = None, *, name: str = "crewai-agent",
                 default_work_type: str = "research", endpoint: Optional[str] = None,
                 client: Optional[MintClient] = None, **kwargs):
        super().__init__(**kwargs)
        # pydantic-based BaseTool: stash on the instance dict to avoid field clashes
        object.__setattr__(self, "_mint", client or MintClient(
            api_key=api_key, endpoint=endpoint, name=name))
        object.__setattr__(self, "_default_work_type", default_work_type)

    def _run(self, summary: str, work_type: Optional[str] = None,
             input_data=None, output_data=None) -> str:
        try:
            r = self._mint.attest(
                work_type=work_type or self._default_work_type,
                input_data=input_data, output_data=output_data or summary,
                duration_seconds=1, summary=summary)
            return (f"Attested on MINT. attestation_id={r.attestation_id} "
                    f"verify={r.verify_url or '(pending)'}")
        except MintError as e:
            log.warning("mint-attest: crewai attestation failed (%s)", e)
            return f"Attestation failed: {e}"


def mint_attest_step_callback(api_key: Optional[str] = None, *, name: str = "crewai-agent",
                              work_type: str = "research", endpoint: Optional[str] = None,
                              client: Optional[MintClient] = None):
    """Return a callable for Crew(step_callback=…) / Task(callback=…) that attests
    each step/task output automatically (no agent tool call needed)."""
    mint = client or MintClient(api_key=api_key, endpoint=endpoint, name=name)

    def _cb(step_output):
        start = time.time()
        try:
            mint.attest(work_type=work_type, output_data=str(step_output),
                        duration_seconds=time.time() - start, summary="crewai step")
        except MintError as e:
            log.warning("mint-attest: crewai step attestation skipped (%s)", e)
    return _cb
