"""ScriptTool — wraps customer BI scripts as Agent-callable Tools."""
from __future__ import annotations

import json
import subprocess
import uuid
from dataclasses import dataclass, field
from typing import Any

from petfishframework.core.contracts import RiskLevel, ToolResult

from petfish_bi_cli.grounding.claims import Claim, ClaimsRegistry

_MAX_OUTPUT = 1_048_576


@dataclass(frozen=True)
class ScriptConfig:
    command: str
    description: str
    input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})
    output_format: str = "json"
    timeout_s: int = 30
    risk_level: str = "medium"
    capabilities: tuple[str, ...] = ("data:read",)


class ScriptTool:
    """Wraps a customer BI script as an Agent-callable Tool."""

    def __init__(self, script_id: str, config: ScriptConfig, registry: ClaimsRegistry):
        self._script_id = script_id
        self._config = config
        self._registry = registry
        self._claim_counter = 0

        self.name = f"run_{script_id}"
        self.description = config.description
        self.input_schema = config.input_schema
        self.risk_level = RiskLevel.LOW if config.risk_level == "low" else RiskLevel.MEDIUM
        self.capabilities = config.capabilities
        self.side_effect = True
        self.idempotent = False
        self.external_egress = False
        self.requires_credentials = False
        self.credential_name: str | None = None

    def execute(self, args: dict[str, Any]) -> ToolResult:
        try:
            result = subprocess.run(
                self._config.command,
                shell=True,
                input=json.dumps(args),
                capture_output=True,
                text=True,
                timeout=self._config.timeout_s,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(error=f"Script timed out after {self._config.timeout_s}s")

        if result.returncode != 0:
            return ToolResult(
                error=f"Script exited {result.returncode}: {result.stderr.strip()[:200]}"
            )

        output = result.stdout[:_MAX_OUTPUT]
        return self._parse_and_register(output)

    def _parse_and_register(self, output: str) -> ToolResult:
        if self._config.output_format == "json":
            try:
                data = json.loads(output)
            except json.JSONDecodeError as exc:
                return ToolResult(error=f"Script output not valid JSON: {exc}")
            claims = self._register_json_claims(data)
            return ToolResult(value={"output": data, "claims": claims})

        return ToolResult(value={"output": output})

    def _register_json_claims(self, data: dict | list) -> list[dict]:
        claims: list[dict] = []
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            for key, value in item.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    claim = self._make_claim(
                        metric=f"{self.name}.{key}",
                        value=float(value),
                        computation="script_output",
                    )
                    claims.append(
                        {"id": claim.id, "metric": claim.metric, "value": claim.value}
                    )
        return claims

    def _make_claim(self, metric: str, value: float, computation: str) -> Claim:
        self._claim_counter += 1
        claim = Claim(
            id=f"sc{self._claim_counter}_{uuid.uuid4().hex[:6]}",
            metric=metric,
            value=value,
            source=self.name,
            computation=computation,
        )
        self._registry.add(claim)
        return claim
