from __future__ import annotations

from petfish_bi_cli.config.prompt_manager import PromptManager


def create_prompt_manager(configs_dir=None) -> PromptManager:
    from pathlib import Path

    if configs_dir is None:
        configs_dir = Path("configs")
    prompt_cfg_path = configs_dir / "prompts.yml"
    if prompt_cfg_path.exists():
        import yaml

        with open(prompt_cfg_path) as f:
            cfg = yaml.safe_load(f) or {}
    else:
        cfg = {
            "system_prompt": {
                "file": str(configs_dir / "prompts" / "system_prompt.md"),
            },
            "few_shot": {
                "mode": "dynamic",
                "pool_dir": str(configs_dir / "prompts" / "few_shot"),
                "k": 3,
                "selection": "intent-first",
                "fallback": "static",
            },
        }
    return PromptManager(config=cfg)
