"""Tests for Reflexion, PolicyHotReload, ConversationStore, ScriptSandbox."""
from __future__ import annotations

import os
import sys
import time

from typer.testing import CliRunner

from petfish_bi_cli.main import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# P2-a: Reflexion wrapping BIAgentStrategy
# ---------------------------------------------------------------------------

class TestReflexionConfig:
    def test_reflexion_disabled_by_default(self):
        from petfish_bi_cli.config.settings import load_settings

        settings = load_settings()
        assert not settings.raw.get("reasoning", {}).get("reflexion", False)

    def test_framework_creates_agent_with_reflexion(self):
        from petfish_bi_cli.framework import make_bi_agent

        agent = make_bi_agent()
        assert agent is not None
        assert agent.reasoning is not None

    def test_framework_with_reflexion_enabled(self):
        from petfish_bi_cli.framework import _should_use_reflexion

        assert _should_use_reflexion({"reasoning": {"reflexion": True}}) is True
        assert _should_use_reflexion({}) is False
        assert _should_use_reflexion({"reasoning": {}}) is False


# ---------------------------------------------------------------------------
# P2-b: PolicyHotReloader
# ---------------------------------------------------------------------------

class TestPolicyHotReload:
    def test_web_command_starts_hot_reloader(self):
        result = runner.invoke(app, ["web", "--help"])
        assert result.exit_code == 0

    def test_hot_reloader_detects_change(self, tmp_path):
        from petfishframework.policies.hot_reload import PolicyHotReloader

        policy_file = tmp_path / "policy.yml"
        policy_file.write_text(
            'version: "1.0"\nname: "test"\nrules:\n'
            '  - name: "default"\n    priority: 0\n    when: {}\n    effect: ALLOW\n'
        )
        reloader = PolicyHotReloader(str(policy_file), check_interval_s=0.1)
        reloader.start()
        try:
            assert reloader.current_policy() is not None
            reloader.stop()

            policy_file.write_text(
                'version: "1.0"\nname: "test-v2"\nrules:\n'
                '  - name: "default"\n    priority: 0\n    when: {}\n    effect: ALLOW\n'
            )
            now_ns = int(time.time() * 1e9 + 1e6)
            os.utime(policy_file, ns=(now_ns, now_ns))
            reloaded = reloader.reload_now()
            assert reloaded is True
        finally:
            reloader.stop()


# ---------------------------------------------------------------------------
# P3: ConversationStore
# ---------------------------------------------------------------------------

class TestConversationStore:
    def test_store_and_load(self):
        from petfishframework.core.conversation import InMemoryConversationStore
        from petfishframework.core.types import Message, Role

        store = InMemoryConversationStore()
        msgs = [Message(role=Role.USER, content="hello")]
        store.save("conv1", msgs)
        loaded = store.load("conv1")
        assert len(loaded) == 1
        assert loaded[0].content == "hello"

    def test_load_nonexistent_returns_empty(self):
        from petfishframework.core.conversation import InMemoryConversationStore

        store = InMemoryConversationStore()
        assert store.load("nonexistent") == []

    def test_clear(self):
        from petfishframework.core.conversation import InMemoryConversationStore
        from petfishframework.core.types import Message, Role

        store = InMemoryConversationStore()
        store.save("conv1", [Message(role=Role.USER, content="hi")])
        store.clear("conv1")
        assert store.load("conv1") == []


# ---------------------------------------------------------------------------
# P1-b: ScriptTool sandbox env filtering
# ---------------------------------------------------------------------------

class TestScriptSandboxEnv:
    def test_env_filtering_blocks_secrets(self, tmp_path):
        from petfish_bi_cli.agent.tools.script import ScriptConfig, ScriptTool
        from petfish_bi_cli.grounding.claims import ClaimsRegistry

        os.environ["SECRET_KEY"] = "leaked-secret-123"
        script = tmp_path / "check_env.py"
        script.write_text(
            "import os, sys, json\n"
            "secret = os.environ.get('SECRET_KEY', 'NOT_FOUND')\n"
            "path = os.environ.get('PATH', 'NOT_FOUND')\n"
            "print(json.dumps({'secret': secret, "
            "'has_path': bool(path and path != 'NOT_FOUND')}))\n"
        )
        cfg = ScriptConfig(
            command=f"{sys.executable} {script}",
            description="check env",
            sandbox_env=True,
        )
        tool = ScriptTool("env_check", cfg, ClaimsRegistry())
        result = tool.execute({})
        assert result.error is None
        assert result.value["output"]["secret"] == "NOT_FOUND"
        assert result.value["output"]["has_path"] is True
        del os.environ["SECRET_KEY"]

    def test_sandbox_disabled_keeps_env(self, tmp_path):
        from petfish_bi_cli.agent.tools.script import ScriptConfig, ScriptTool
        from petfish_bi_cli.grounding.claims import ClaimsRegistry

        os.environ["TEST_VAR_xyz"] = "present"
        script = tmp_path / "check_env2.py"
        script.write_text(
            "import os, json\n"
            "print(json.dumps({'val': os.environ.get('TEST_VAR_xyz', 'MISSING')}))\n"
        )
        cfg = ScriptConfig(
            command=f"{sys.executable} {script}",
            description="check env no sandbox",
            sandbox_env=False,
        )
        tool = ScriptTool("env_check2", cfg, ClaimsRegistry())
        result = tool.execute({})
        assert result.value["output"]["val"] == "present"
        del os.environ["TEST_VAR_xyz"]
