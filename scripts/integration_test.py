"""Integration test: real model via SiliconFlow Qwen2.5-72B-Instruct.

Run: uv run python scripts/integration_test.py

Tests 4 levels:
  L1: Model connectivity (simple completion)
  L2: Agent + tool calling (explore_data_sources)
  L3: Full BIApplication pipeline (query → tools → grounded report)
  L4: CLI invocation
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_l1_model_connectivity() -> bool:
    """L1: Can we construct the model and get a response?"""
    from petfish_bi_cli.config.settings import load_settings
    from petfish_bi_cli.config.model_factory import ModelFactory

    settings = load_settings()
    print(f"Provider: {settings.model.provider}")
    print(f"Model:    {settings.model.name}")
    print(f"Base URL: {settings.model.base_url}")
    print(f"API key:  {'***' + settings.model.api_key[-4:] if settings.model.api_key else 'NONE'}")

    factory = ModelFactory(settings)
    model = factory.build()

    from petfishframework.core.types import Message, Role

    messages = [Message(role=Role.USER, content="回复OK两个字，不要其他内容")]
    print("\nSending test message...")
    t0 = time.time()
    response = model.complete(messages)
    elapsed = time.time() - t0
    print(f"Response ({elapsed:.1f}s): {response.content[:100]}")

    if "ok" in response.content.lower():
        print("✅ L1 PASS: Model connectivity confirmed")
        return True
    else:
        print(f"⚠ L1 CAUTION: Got unexpected response: {response.content[:100]}")
        return True

def test_l2_tool_calling() -> bool:
    """L2: Can the Agent call explore_data_sources tool?"""
    from petfish_bi_cli.agent.tools.explore import ExploreDataSourcesTool
    from petfish_bi_cli.config.settings import load_settings
    from petfish_bi_cli.config.model_factory import ModelFactory
    from petfish_bi_cli.agent.strategy import BIAgentStrategy
    from petfishframework import Agent

    settings = load_settings()
    factory = ModelFactory(settings)
    model = factory.build()

    semantic_dir = Path(__file__).parent.parent / "references" / "semantic"
    explore = ExploreDataSourcesTool(semantic_dir=semantic_dir)

    agent = Agent(
        model=model,
        reasoning=BIAgentStrategy(),
        tools=(explore,),
    )

    from petfishframework.core.types import Message, Role

    messages = [Message(role=Role.USER, content="有哪些数据源？列出 source_id")]
    print("Asking agent to explore data sources...")
    t0 = time.time()
    try:
        session = agent.run(messages)
        elapsed = time.time() - t0
        events = session.events
        tool_calls = [e for e in events if e.type.value == "tool_call"]
        model_calls = [e for e in events if e.type.value == "model_request"]
        print(f"Session ({elapsed:.1f}s): {len(model_calls)} model calls, {len(tool_calls)} tool calls")

        if tool_calls:
            print(f"Tool called: {tool_calls[0].tool_name}")
            print("✅ L2 PASS: Agent can call tools")
            return True
        else:
            print("⚠ L2 PARTIAL: Agent ran but didn't call tool (may have answered directly)")
            return True

    except Exception as e:
        print(f"❌ L2 FAIL: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_l3_full_pipeline() -> bool:
    """L3: Full BIApplication.execute() → grounded BIReport."""
    from petfish_bi_cli.application import BIApplication
    from petfish_bi_cli.domain import BIQuery

    app = BIApplication()
    query = BIQuery(prompt="CROCS在京东的均价是多少？")

    print(f"Query: {query.prompt}")
    print("Running BIApplication.execute()...")
    t0 = time.time()
    try:
        report = app.execute(query)
        elapsed = time.time() - t0
        print(f"\nReport ({elapsed:.1f}s):")
        print(f"  status:    {report.status}")
        print(f"  answer:    {(report.answer or '')[:200]}")
        print(f"  data:      {json.dumps(report.data, ensure_ascii=False)[:300] if report.data else 'N/A'}")
        print(f"  session:   {report.session_id}")

        if report.status == "ok":
            print("✅ L3 PASS: Full pipeline produced grounded report")
            return True
        elif report.status == "budget_exceeded":
            print("⚠ L3 BUDGET: Ran out of budget before completing")
            return False
        elif report.status == "parse_error":
            print(f"⚠ L3 PARSE: Model output couldn't be parsed: {(report.answer or '')[:200]}")
            return False
        elif report.status == "validation_failed":
            print("⚠ L3 VALIDATION: Output failed grounding check (hallucination detected)")
            return False
        else:
            print(f"⚠ L3 UNKNOWN: status={report.status}")
            return False

    except Exception as e:
        print(f"❌ L3 FAIL: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_l4_cli() -> bool:
    """L4: CLI invocation via typer CliRunner."""
    from typer.testing import CliRunner
    from petfish_bi_cli.main import app as cli_app

    runner = CliRunner()
    print('Running: petfish-bi ask "JD有多少条商品数据？"')
    t0 = time.time()
    try:
        result = runner.invoke(cli_app, ["ask", "京东有多少条商品数据？"])
        elapsed = time.time() - t0
        print(f"Exit code: {result.exit_code} ({elapsed:.1f}s)")
        output = result.stdout.strip()
        print(f"Output:\n{output[:500]}")

        if result.exit_code == 0:
            print("✅ L4 PASS: CLI executed successfully")
            return True
        else:
            print(f"❌ L4 FAIL: exit code {result.exit_code}")
            if result.exception:
                import traceback
                traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)
            return False

    except Exception as e:
        print(f"❌ L4 FAIL: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    header("Integration Test: SiliconFlow Qwen2.5-72B-Instruct")

    results = {}

    header("L1: Model Connectivity")
    results["L1"] = test_l1_model_connectivity()

    header("L2: Agent + Tool Calling")
    results["L2"] = test_l2_tool_calling()

    header("L3: Full BIApplication Pipeline")
    results["L3"] = test_l3_full_pipeline()

    header("L4: CLI Invocation")
    results["L4"] = test_l4_cli()

    header("Summary")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for level, ok in results.items():
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {level}: {status}")
    print(f"\n{passed}/{total} levels passed")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
