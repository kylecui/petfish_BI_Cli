from __future__ import annotations

import re

from petfish_bi_cli.grounding.claims import ClaimsLedger, ValidationResult


def validate_report(
    report_answer: str,
    report_data: dict,
    claims: ClaimsLedger,
) -> ValidationResult:
    """Validate that every number in the report traces to a claim."""
    errors: list[str] = []

    claim_map = claims.by_id()
    claim_value_strs = [str(c.value) for c in claims.claims]

    findings = report_data.get("findings", [])
    if isinstance(findings, list):
        for i, finding in enumerate(findings):
            if not isinstance(finding, dict):
                continue
            cid = finding.get("claim_id")
            val = finding.get("value")

            if cid and cid in claim_map:
                if val is not None and val != claim_map[cid].value:
                    errors.append(
                        f"Finding {i}: claim {cid} value mismatch "
                        f"(report={val}, claim={claim_map[cid].value})"
                    )
            elif val is not None and isinstance(val, (int, float)):
                errors.append(f"Finding {i}: unverified value {val} (no matching claim)")

    numbers = re.findall(r"\d+\.?\d*", report_answer)
    for num in numbers:
        if not any(num in cv for cv in claim_value_strs):
            if len(num) > 1 or num not in ("0", "1"):
                errors.append(f"Number '{num}' in answer not found in any claim")

    return ValidationResult(valid=len(errors) == 0, errors=tuple(errors))
