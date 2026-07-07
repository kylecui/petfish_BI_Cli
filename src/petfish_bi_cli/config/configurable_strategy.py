from __future__ import annotations

from petfish_bi_cli.config.prompt_manager import PromptManager
from petfish_bi_cli.agent.strategy import BIAgentStrategy


class ConfigurableBIAgentStrategy(BIAgentStrategy):
    """BIAgentStrategy that reads system prompt + few-shot from PromptManager."""

    def __init__(self, prompt_manager: PromptManager):
        self._pm = prompt_manager
        self._query: str = ""
        self._intent: str | None = None

    def _system_prompt(self, tools: list) -> str:
        from petfishframework.reasoning.react import ReAct
        base = ReAct._system_prompt(self, tools)
        bi_prompt = self._pm.load_system_prompt()
        few_shot = self._pm.select_few_shot(self._query, self._intent)
        parts = [p for p in [bi_prompt, few_shot, base] if p]
        return "\n\n".join(parts)
