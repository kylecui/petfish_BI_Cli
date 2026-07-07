from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PromptManager:
    """Manages system prompt and few-shot examples from config.

    Features:
    - Hot-reload: checks file mtime, reloads if changed
    - Dynamic few-shot selection: intent-first or static
    - Version tracking: reads 'version' from config
    """

    config: dict[str, Any]
    _cache: dict[str, tuple[str, float]] = field(default_factory=dict, repr=False)

    def load_system_prompt(self) -> str:
        cfg = self.config.get("system_prompt", {})
        file_path = Path(cfg.get("file", "configs/prompts/system_prompt.md"))
        content = self._load_with_cache(file_path)

        version = cfg.get("version", "1.0.0")
        header = f"<!-- prompt version: {version} -->\n"
        return header + content

    def select_few_shot(self, query: str, intent: str | None = None) -> str:
        cfg = self.config.get("few_shot", {})
        mode = cfg.get("mode", "off")

        if mode == "off":
            return ""

        pool_dir = Path(cfg.get("pool_dir", "configs/prompts/few_shot/"))
        k = cfg.get("k", 3)
        strategy = cfg.get("selection", "intent-first")

        examples = self._load_pool(pool_dir)
        if not examples:
            return ""

        selected = self._select(examples, query, intent, k, strategy)
        return self._format_examples(selected)

    def get_version(self) -> str:
        return self.config.get("system_prompt", {}).get("version", "unknown")

    def _load_with_cache(self, path: Path) -> str:
        if not path.exists():
            return _DEFAULT_SYSTEM_PROMPT

        mtime = path.stat().st_mtime
        cache_key = str(path)

        cached = self._cache.get(cache_key)
        if cached and cached[1] == mtime:
            return cached[0]

        content = path.read_text(encoding="utf-8")
        self._cache[cache_key] = (content, mtime)
        return content

    def _load_pool(self, pool_dir: Path) -> list[dict[str, str]]:
        if not pool_dir.exists():
            return []

        examples: list[dict[str, str]] = []
        for ext in ("*.txt", "*.md", "*.yaml", "*.yml"):
            for file_path in sorted(pool_dir.glob(ext)):
                content = file_path.read_text(encoding="utf-8")
                if file_path.suffix in (".yaml", ".yml"):
                    parsed = yaml.safe_load(content)
                    if isinstance(parsed, dict):
                        examples.append({
                            "input": parsed.get("input", ""),
                            "output": parsed.get("output", ""),
                            "intent": parsed.get("intent", ""),
                        })
                else:
                    intent_tag = file_path.stem
                    examples.append({
                        "input": content,
                        "output": "",
                        "intent": intent_tag,
                    })
        return examples

    def _select(
        self,
        examples: list[dict[str, str]],
        query: str,
        intent: str | None,
        k: int,
        strategy: str,
    ) -> list[dict[str, str]]:
        if strategy == "intent-first" and intent:
            matched = [ex for ex in examples if ex.get("intent") == intent]
            if len(matched) >= 1:
                return matched[:k]

        if strategy == "static":
            return examples[:k]

        return examples[:k]

    def _format_examples(self, examples: list[dict[str, str]]) -> str:
        parts: list[str] = []
        for ex in examples:
            if ex.get("output"):
                parts.append(f"User: {ex['input']}\n{ex['output']}")
            else:
                parts.append(ex["input"])
        return "\n\n".join(parts) if parts else ""


def load_prompt_config(config_path: str | Path = "configs/bi_cli.yml") -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return raw.get("prompts", {})


_DEFAULT_SYSTEM_PROMPT = """你是 BI 数据分析 Agent。你通过 Tool 获取数据，仅基于实际数据回答问题。
不要使用模型训练数据中的知识来替代真实数据。
每个输出中的数字必须引用 Tool 返回的 claim ID。"""
