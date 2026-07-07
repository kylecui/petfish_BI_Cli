from __future__ import annotations

import pytest

from petfish_bi_cli.agent.tools.analyze import analyze_claims


class TestAnalyzeClaims:
    def test_avg(self):
        claim = analyze_claims([100.0, 200.0, 300.0], "avg")
        assert claim.value == 200.0
        assert claim.metric == "avg"

    def test_sum(self):
        claim = analyze_claims([100.0, 200.0], "sum")
        assert claim.value == 300.0

    def test_min(self):
        claim = analyze_claims([100.0, 50.0, 200.0], "min")
        assert claim.value == 50.0

    def test_max(self):
        claim = analyze_claims([100.0, 50.0, 200.0], "max")
        assert claim.value == 200.0

    def test_count(self):
        claim = analyze_claims([100.0, 200.0, 300.0], "count")
        assert claim.value == 3.0

    def test_compare(self):
        claim = analyze_claims([489.0, 407.01], "compare")
        assert claim.value == 81.99
        assert "pct=" in claim.computation

    def test_compare_requires_two_values(self):
        with pytest.raises(ValueError, match="at least 2"):
            analyze_claims([100.0], "compare")

    def test_unknown_operation(self):
        with pytest.raises(ValueError, match="Unknown operation"):
            analyze_claims([1.0], "median")

    def test_empty_values(self):
        claim = analyze_claims([], "avg")
        assert claim.value == 0

    def test_claim_has_id(self):
        claim = analyze_claims([100.0], "avg")
        assert claim.id.startswith("c")
        assert len(claim.id) > 1
