"""Tests for ScriptTool — customer BI script wrapper."""
from __future__ import annotations

import sys
from pathlib import Path

from petfish_bi_cli.agent.tools.script import ScriptConfig, ScriptTool
from petfish_bi_cli.grounding.claims import ClaimsRegistry


def _make_echo_script(tmp_path: Path) -> Path:
    """Create a test script that echoes JSON output from stdin args."""
    script = tmp_path / "echo_script.py"
    script.write_text(
        "import json, sys\n"
        "args = json.loads(sys.stdin.read())\n"
        "print(json.dumps({'total_sales': 12345.67, "
        "'item_count': 42, 'name': args.get('name', 'default')}))\n",
        encoding="utf-8",
    )
    return script


def _make_failing_script(tmp_path: Path) -> Path:
    script = tmp_path / "fail_script.py"
    script.write_text("import sys; sys.exit(1)", encoding="utf-8")
    return script


def _make_slow_script(tmp_path: Path) -> Path:
    script = tmp_path / "slow_script.py"
    script.write_text("import time; time.sleep(10)", encoding="utf-8")
    return script


class TestScriptConfig:
    def test_defaults(self):
        cfg = ScriptConfig(
            command="python test.py",
            description="test",
        )
        assert cfg.timeout_s == 30
        assert cfg.output_format == "json"
        assert cfg.capabilities == ("data:read",)

    def test_risk_level_from_string(self):
        cfg = ScriptConfig(command="x", description="x", risk_level="high")
        assert cfg.risk_level == "high"


class TestScriptToolExecution:
    def test_executes_command_and_parses_json_output(self, tmp_path):
        script = _make_echo_script(tmp_path)
        cfg = ScriptConfig(
            command=f"{sys.executable} {script}",
            description="echo test",
            input_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        )
        tool = ScriptTool("echo", cfg, ClaimsRegistry())
        result = tool.execute({"name": "CROCS"})
        assert result.error is None
        assert result.value["output"]["total_sales"] == 12345.67
        assert result.value["output"]["item_count"] == 42

    def test_registers_claims_from_numeric_fields(self, tmp_path):
        script = _make_echo_script(tmp_path)
        cfg = ScriptConfig(command=f"{sys.executable} {script}", description="test")
        reg = ClaimsRegistry()
        tool = ScriptTool("echo", cfg, reg)
        tool.execute({"name": "test"})
        assert reg.count >= 2
        ledger = reg.to_ledger()
        claim_metrics = [c.metric for c in ledger.claims]
        assert any("total_sales" in m for m in claim_metrics)
        assert any("item_count" in m for m in claim_metrics)

    def test_nonzero_exit_returns_error(self, tmp_path):
        script = _make_failing_script(tmp_path)
        cfg = ScriptConfig(command=f"{sys.executable} {script}", description="fail")
        tool = ScriptTool("fail", cfg, ClaimsRegistry())
        result = tool.execute({})
        assert result.error is not None
        assert "exited" in result.error.lower() or "fail" in result.error.lower()

    def test_timeout_returns_error(self, tmp_path):
        script = _make_slow_script(tmp_path)
        cfg = ScriptConfig(
            command=f"{sys.executable} {script}",
            description="slow",
            timeout_s=1,
        )
        tool = ScriptTool("slow", cfg, ClaimsRegistry())
        result = tool.execute({})
        assert result.error is not None

    def test_text_output_format(self, tmp_path):
        script = tmp_path / "text_script.py"
        script.write_text("print('hello world')")
        cfg = ScriptConfig(
            command=f"{sys.executable} {script}",
            description="text output",
            output_format="text",
        )
        tool = ScriptTool("text", cfg, ClaimsRegistry())
        result = tool.execute({})
        assert result.error is None
        assert "hello" in result.value["output"]


class TestScriptToolAttributes:
    def test_name_uses_prefix(self):
        cfg = ScriptConfig(command="x", description="x")
        tool = ScriptTool("sales_report", cfg, ClaimsRegistry())
        assert tool.name == "run_sales_report"

    def test_description_from_config(self):
        cfg = ScriptConfig(command="x", description="生成销售报表")
        tool = ScriptTool("sales", cfg, ClaimsRegistry())
        assert "销售报表" in tool.description

    def test_side_effect_true_by_default(self):
        cfg = ScriptConfig(command="x", description="x")
        tool = ScriptTool("s", cfg, ClaimsRegistry())
        assert tool.side_effect is True
        assert tool.idempotent is False

    def test_protocol_fields(self):
        cfg = ScriptConfig(command="x", description="x")
        tool = ScriptTool("s", cfg, ClaimsRegistry())
        assert tool.risk_level is not None
        assert tool.capabilities == ("data:read",)
        assert tool.requires_credentials is False
