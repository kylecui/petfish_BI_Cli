from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from petfish_bi_cli.grounding.claims import ClaimsLedger

_CN_NUM_MAP = {
    "零": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "百": 100,
    "千": 1000,
    "万": 10000,
    "两": 2,
}


def cn_to_num(text: str) -> float | None:
    text = text.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        pass
    if all(c in _CN_NUM_MAP for c in text):
        total = 0
        current = 0
        for char in text:
            val = _CN_NUM_MAP[char]
            if val >= 10:
                if current == 0:
                    current = 1
                total += current * val
                current = 0
            else:
                current = val
        total += current
        return float(total) if total > 0 else None
    return None


def extract_numbers(text: str) -> list[float]:
    numbers: list[float] = []
    for match in re.finditer(r"[\d,]+\.?\d*", text):
        raw = match.group().replace(",", "")
        try:
            numbers.append(float(raw))
        except ValueError:
            pass
    for match in re.finditer(r"[零一二三四五六七八九十百千万两]+", text):
        val = cn_to_num(match.group())
        if val is not None:
            numbers.append(val)
    return numbers


def _levenshtein_ratio(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            tmp = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(dp[j], dp[j - 1], prev)
            prev = tmp
    distance = dp[n]
    return 1.0 - distance / max(m, n)


@dataclass(frozen=True)
class EnhancedValidationResult:
    valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    verified_numbers: tuple[float, ...] = ()
    unverified_numbers: tuple[float, ...] = ()
    truth_labels: tuple[str, ...] = ()


def validate_report_enhanced(
    report_answer: str,
    report_data: dict[str, Any],
    claims: ClaimsLedger,
    fuzzy_threshold: float = 0.8,
) -> EnhancedValidationResult:
    claim_values: dict[str, float] = {}
    for claim in claims.claims:
        claim_values[claim.id] = (
            float(claim.value) if isinstance(claim.value, (int, float)) else 0.0
        )

    all_claim_nums = set(claim_values.values())
    answer_numbers = extract_numbers(report_answer)
    data_numbers: list[float] = []
    findings = report_data.get("findings", [])
    if isinstance(findings, list):
        for finding in findings:
            if isinstance(finding, dict):
                val = finding.get("value")
                if isinstance(val, (int, float)):
                    data_numbers.append(float(val))

    verified: list[float] = []
    unverified: list[float] = []
    errors: list[str] = []
    warnings: list[str] = []
    truth_labels: list[str] = []

    for num in answer_numbers:
        matched = False
        for claim_val in all_claim_nums:
            if abs(num - claim_val) < 0.01:
                verified.append(num)
                truth_labels.append(f"T1:{num}")
                matched = True
                break
        if not matched:
            for claim_val in all_claim_nums:
                if claim_val > 0 and abs(num - claim_val) / claim_val < 0.05:
                    verified.append(num)
                    truth_labels.append(f"T2:{num}~{claim_val}")
                    matched = True
                    warnings.append(f"Number {num} is approximate to claim value {claim_val}")
                    break
        if not matched:
            unverified.append(num)
            truth_labels.append(f"T5:{num}")
            errors.append(f"Unverified number in answer: {num}")

    for num in data_numbers:
        if num in all_claim_nums or any(abs(num - cv) < 0.01 for cv in all_claim_nums):
            continue
        unverified.append(num)
        errors.append(f"Unverified number in data: {num}")

    for finding in findings if isinstance(findings, list) else []:
        if isinstance(finding, dict):
            cid = finding.get("claim_id")
            val = finding.get("value")
            if cid and val is not None:
                if cid not in claim_values:
                    errors.append(f"Finding references unknown claim_id: {cid}")
                elif abs(float(val) - claim_values[cid]) > 0.01:
                    errors.append(f"Value mismatch for {cid}: {val} vs {claim_values[cid]}")

    for finding in findings if isinstance(findings, list) else []:
        if isinstance(finding, dict):
            quote = finding.get("supporting_quote", "")
            if quote:
                best_ratio = 0.0
                for claim_text in [str(c.value) for c in claims.claims]:
                    ratio = _levenshtein_ratio(quote, claim_text)
                    best_ratio = max(best_ratio, ratio)
                if best_ratio < fuzzy_threshold:
                    warnings.append(
                        f"Supporting quote fuzzy match below threshold: {best_ratio:.2f}"
                    )

    valid = len(errors) == 0
    return EnhancedValidationResult(
        valid=valid,
        errors=tuple(errors),
        warnings=tuple(warnings),
        verified_numbers=tuple(verified),
        unverified_numbers=tuple(unverified),
        truth_labels=tuple(truth_labels),
    )
