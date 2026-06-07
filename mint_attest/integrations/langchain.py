"""LangChain integration — attest every chain/agent run.

    from mint_attest.langchain import MintAttestCallback

    chain = LLMChain(llm=llm, prompt=prompt,
                     callbacks=[MintAttestCallback(api_key="fnet_…")])
    chain.run(...)   # automatically attested on MINT

Works with both the new (`langchain_core.callbacks`) and legacy
(`langchain.callbacks.base`) callback base classes.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

from ..client import MintClient
from ..exceptions import MintError

log = logging.getLogger("mint_attest.langchain")


def _base_handler():
    try:
        from langchain_core.callbacks import BaseCallbackHandler  # langchain >= 0.1
        return BaseCallbackHandler
    except Exception:
        pass
    try:
        from langchain.callbacks.base import BaseCallbackHandler  # legacy
        return BaseCallbackHandler
    except Exception as e:
        raise ImportError(
            "LangChain is not installed. `pip install mint-attest[langchain]` "
            "(or `pip install langchain`)."
        ) from e


_Base = _base_handler()


class MintAttestCallback(_Base):  # type: ignore[misc,valid-type]
    """A LangChain callback handler that attests each chain run on MINT."""

    def __init__(self, api_key: Optional[str] = None, *, work_type: str = "generation",
                 name: str = "langchain-agent", endpoint: Optional[str] = None,
                 client: Optional[MintClient] = None, capabilities: Optional[list] = None):
        super().__init__()
        self.client = client or MintClient(api_key=api_key, endpoint=endpoint,
                                            name=name, capabilities=capabilities)
        self.work_type = work_type
        self._starts: dict = {}

    def on_chain_start(self, serialized, inputs, *, run_id=None, **kwargs):
        self._starts[str(run_id)] = (time.time(), inputs)

    def on_chain_end(self, outputs, *, run_id=None, **kwargs):
        start, inputs = self._starts.pop(str(run_id), (time.time(), None))
        try:
            self.client.attest(
                work_type=self.work_type, input_data=inputs, output_data=outputs,
                duration_seconds=time.time() - start, summary="langchain chain run")
        except MintError as e:
            log.warning("mint-attest: langchain attestation skipped (%s)", e)

    def on_chain_error(self, error, *, run_id=None, **kwargs):
        self._starts.pop(str(run_id), None)
