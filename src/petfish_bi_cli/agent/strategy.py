from __future__ import annotations

from datetime import date
from pathlib import Path

from petfishframework.reasoning.react import ReAct

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class BIAgentStrategy(ReAct):
    """ReAct with BI-specific grounding constraints.

    Overrides _system_prompt() to inject:
    - BI role definition
    - Data source summary
    - Grounding rules (ONLY use data from Tools)
    - Output format specification
    """

    def _system_prompt(self, tools: list) -> str:
        base = super()._system_prompt(tools)
        bi_prompt = _load_bi_prompt()
        return bi_prompt + "\n\n" + base


def _load_bi_prompt() -> str:
    prompt_path = PROMPTS_DIR / "system_prompt.md"
    if prompt_path.exists():
        text = prompt_path.read_text(encoding="utf-8")
        return text.replace("{current_date}", date.today().isoformat())
    return _DEFAULT_BI_PROMPT


_DEFAULT_BI_PROMPT = """你是 BI 数据分析 Agent。你通过 Tool 获取数据，仅基于实际数据回答问题。
不要使用模型训练数据中的知识来替代真实数据。
每个输出中的数字必须引用 Tool 返回的 claim ID。"""
