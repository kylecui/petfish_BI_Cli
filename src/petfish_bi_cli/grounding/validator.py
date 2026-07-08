from __future__ import annotations

import re

from petfish_bi_cli.grounding.claims import ClaimsLedger, ValidationResult

COMMON_UNITS = {
    "元",
    "万元",
    "分",
    "个",
    "条",
    "件",
    "家",
    "款",
    "双",
    "瓶",
    "%",
    "倍",
    "天",
    "周",
    "月",
    "年",
    "次",
    "人",
    "类",
}


def validate_report(
    report_answer: str,
    report_data: dict,
    claims: ClaimsLedger,
) -> ValidationResult:
    """Validate that every number in the report traces to a claim."""
    errors: list[str] = []

    claim_map = claims.by_id()
    claim_value_strs = [str(c.value) for c in claims.claims]
    claim_metrics = {c.metric: c for c in claims.claims}
    grounded_nums = claims.all_grounded_numbers()

    findings = report_data.get("findings", [])
    if isinstance(findings, list):
        for i, finding in enumerate(findings):
            if not isinstance(finding, dict):
                continue
            cid = finding.get("claim_id")
            val = finding.get("value")
            metric = finding.get("metric", "")

            if cid and cid in claim_map:
                claim = claim_map[cid]
                if val is not None and not _values_match(val, claim.value):
                    errors.append(
                        f"Finding {i}: claim {cid} value mismatch "
                        f"(report={val}, claim={claim.value})"
                    )
                if metric and claim.metric and metric != claim.metric:
                    if metric not in claim.metric and claim.metric not in metric:
                        errors.append(
                            f"Finding {i}: metric mismatch "
                            f"(finding='{metric}', claim='{claim.metric}')"
                        )
            elif val is not None and isinstance(val, (int, float)):
                matched = False
                if metric and metric in claim_metrics:
                    if _values_match(val, claim_metrics[metric].value):
                        matched = True
                if not matched:
                    errors.append(f"Finding {i}: unverified value {val} for metric '{metric}'")

    numbers = re.findall(r"\d+\.?\d*", report_answer)
    for num in numbers:
        num_float: float
        try:
            num_float = float(num)
            in_grounded = any(
                abs(num_float - g) < 0.01 for g in grounded_nums
            )
        except ValueError:
            in_grounded = False
            num_float = 0.0
        in_claims = any(num in cv for cv in claim_value_strs)
        if not in_grounded and not in_claims:
            if len(num) > 1 or num not in ("0", "1"):
                if not _is_unit_context(report_answer, num):
                    if not _is_derived_from_grounded(num_float, grounded_nums):
                        errors.append(f"Number '{num}' in answer not found in any claim")

    if isinstance(findings, list) and len(findings) > 0:
        findings_with_claims = sum(
            1
            for f in findings
            if isinstance(f, dict) and f.get("claim_id") and f.get("claim_id") in claim_map
        )
        coverage = findings_with_claims / len(findings) if findings else 0
        if coverage < 0.5:
            errors.append(
                f"Low grounding coverage: {findings_with_claims}/{len(findings)} "
                f"findings ({coverage:.0%}) have verified claims"
            )

    return ValidationResult(valid=len(errors) == 0, errors=tuple(errors))


def _values_match(a, b, tolerance: float = 0.01) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a == b:
            return True
        if abs(b) > 0:
            return abs(a - b) / abs(b) < tolerance
        return abs(a - b) < tolerance
    return str(a) == str(b)


def _is_derived_from_grounded(num: float, grounded: set[float], tolerance: float = 0.5) -> bool:
    """Check if a number is derivable from grounded values via diff, sum, or ratio."""
    grounded_list = sorted(grounded)
    for i, a in enumerate(grounded_list):
        for b in grounded_list[i:]:
            if abs(num - abs(a - b)) < tolerance:
                return True
            if abs(num - (a + b)) < tolerance:
                return True
            if b > 0 and abs(num - abs(a - b) / b * 100) < tolerance:
                return True
            if b > 0 and abs(num - a / b * 100) < tolerance:
                return True
    return False


def _is_unit_context(text: str, num: str) -> bool:
    idx = text.find(num)
    if idx < 0:
        return False
    after = text[idx + len(num) : idx + len(num) + 4]
    for unit in COMMON_UNITS:
        if after.startswith(unit):
            return False
    if num in ("1", "2", "3"):
        after_stripped = after.lstrip()
        if after_stripped and after_stripped[0] in "到与和 ":
            return True
    return False
