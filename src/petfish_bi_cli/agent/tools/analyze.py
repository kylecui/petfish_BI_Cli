from __future__ import annotations

import uuid

from petfish_bi_cli.grounding.claims import Claim


def analyze_claims(
    claim_values: list[float],
    operation: str,
    source: str = "analyze",
) -> Claim:
    """Deterministic computation on claim values. Returns a new Claim with the result."""
    if not claim_values:
        return Claim(
            id=f"c{uuid.uuid4().hex[:8]}",
            metric=operation,
            value=0,
            source=source,
            computation=f"{operation}(empty)",
        )

    if operation == "avg":
        result = sum(claim_values) / len(claim_values)
    elif operation == "sum":
        result = sum(claim_values)
    elif operation == "min":
        result = min(claim_values)
    elif operation == "max":
        result = max(claim_values)
    elif operation == "count":
        result = float(len(claim_values))
    elif operation == "compare":
        if len(claim_values) < 2:
            raise ValueError("compare requires at least 2 values")
        diff = claim_values[0] - claim_values[1]
        pct = (diff / claim_values[1] * 100) if claim_values[1] != 0 else 0.0
        result = round(diff, 2)
        return Claim(
            id=f"c{uuid.uuid4().hex[:8]}",
            metric="price_diff",
            value=result,
            source=source,
            computation=f"compare({claim_values[0]} - {claim_values[1]}) = {diff}, pct={pct:.1f}%",
        )
    else:
        raise ValueError(f"Unknown operation: {operation}")

    return Claim(
        id=f"c{uuid.uuid4().hex[:8]}",
        metric=operation,
        value=round(result, 2) if isinstance(result, float) else result,
        source=source,
        computation=f"{operation}({claim_values}) = {result}",
    )
