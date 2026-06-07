"""AutoGen integration — attest an agent's replies.

    from mint_attest.autogen import MintAttestHook

    hook = MintAttestHook(api_key="fnet_…")
    agent = AssistantAgent("reviewer", llm_config=...)
    hook.attach(agent)        # every generated reply is attested on MINT

AutoGen's hook surface differs across versions, so we register on whatever the
installed version exposes: the modern `register_hook("process_message_before_send")`
if present, else `register_reply`. The hook NEVER alters the message/reply — it
only observes and attests.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from ..client import MintClient
from ..exceptions import MintError

log = logging.getLogger("mint_attest.autogen")


class MintAttestHook:
    """Observes an AutoGen agent's outgoing replies and attests each on MINT."""

    def __init__(self, api_key: Optional[str] = None, *, work_type: str = "generation",
                 name: str = "autogen-agent", endpoint: Optional[str] = None,
                 client: Optional[MintClient] = None):
        self.client = client or MintClient(api_key=api_key, endpoint=endpoint, name=name)
        self.work_type = work_type

    def _attest(self, content) -> None:
        start = time.time()
        try:
            self.client.attest(work_type=self.work_type, output_data=content,
                               duration_seconds=time.time() - start, summary="autogen reply")
        except MintError as e:
            log.warning("mint-attest: autogen attestation skipped (%s)", e)

    def attach(self, agent) -> "MintAttestHook":
        """Register on `agent` using whatever hook API its AutoGen version has."""
        # modern hookable method (pyautogen >= 0.2): observe before send, pass-through
        if hasattr(agent, "register_hook"):
            def _before_send(sender=None, message=None, recipient=None, silent=None):
                content = message.get("content") if isinstance(message, dict) else message
                if content:
                    self._attest(content)
                return message            # MUST return the message unchanged
            try:
                agent.register_hook("process_message_before_send", _before_send)
                return self
            except Exception as e:
                log.debug("register_hook unavailable for this method (%s); trying register_reply", e)

        # fallback: register_reply observer (never produces a reply → returns False)
        if hasattr(agent, "register_reply"):
            def _observer(recipient, messages=None, sender=None, config=None):
                if messages:
                    last = messages[-1]
                    content = last.get("content") if isinstance(last, dict) else last
                    if content:
                        self._attest(content)
                return False, None        # not handled → normal flow continues
            agent.register_reply([object], _observer, position=0)
            return self

        raise TypeError(
            "Could not attach MintAttestHook: this AutoGen agent exposes neither "
            "register_hook nor register_reply. Attest manually via MintClient.attest().")
