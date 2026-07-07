from __future__ import annotations

import pytest

from petfish_bi_cli.grounding.claims import (
    Claim,
    ClaimsLedger,
    ClaimsRegistry,
    ValidationResult,
)


class TestClaim:
    def test_claim_is_frozen(self):
        c = Claim(id="c1", metric="avg_price", value=489.0, source="jd_products")
        with pytest.raises(AttributeError):
            c.value = 999.0

    def test_claim_defaults(self):
        c = Claim(id="c1", metric="price", value=100.0, source="jd")
        assert c.source_rows == ()
        assert c.computation == ""


class TestClaimsLedger:
    def test_by_id(self):
        c1 = Claim(id="c1", metric="price", value=100.0, source="jd")
        c2 = Claim(id="c2", metric="price", value=200.0, source="tmall")
        ledger = ClaimsLedger(claims=(c1, c2))
        assert ledger.by_id()["c1"] == c1
        assert ledger.by_id()["c2"] == c2

    def test_values(self):
        c1 = Claim(id="c1", metric="price", value=100.0, source="jd")
        c2 = Claim(id="c2", metric="price", value=200.0, source="tmall")
        ledger = ClaimsLedger(claims=(c1, c2))
        assert ledger.values() == [100.0, 200.0]

    def test_merge(self):
        c1 = Claim(id="c1", metric="price", value=100.0, source="jd")
        c2 = Claim(id="c2", metric="price", value=200.0, source="tmall")
        l1 = ClaimsLedger(claims=(c1,), metadata={"a": 1})
        l2 = ClaimsLedger(claims=(c2,), metadata={"b": 2})
        merged = l1.merge(l2)
        assert len(merged.claims) == 2
        assert merged.metadata == {"a": 1, "b": 2}

    def test_empty_ledger(self):
        ledger = ClaimsLedger()
        assert ledger.by_id() == {}
        assert ledger.values() == []


class TestClaimsRegistry:
    def test_add_and_to_ledger(self):
        reg = ClaimsRegistry()
        c1 = Claim(id="c1", metric="price", value=100.0, source="jd")
        reg.add(c1)
        ledger = reg.to_ledger()
        assert ledger.claims == (c1,)

    def test_reset(self):
        reg = ClaimsRegistry()
        reg.add(Claim(id="c1", metric="price", value=100.0, source="jd"))
        assert reg.count == 1
        reg.reset()
        assert reg.count == 0
        assert reg.to_ledger().claims == ()

    def test_count(self):
        reg = ClaimsRegistry()
        assert reg.count == 0
        reg.add(Claim(id="c1", metric="a", value=1, source="s"))
        reg.add(Claim(id="c2", metric="b", value=2, source="s"))
        assert reg.count == 2


class TestValidationResult:
    def test_valid_result(self):
        r = ValidationResult(valid=True)
        assert r.valid is True
        assert r.errors == ()

    def test_invalid_result_with_errors(self):
        r = ValidationResult(
            valid=False,
            errors=("Unverified value: 999", "Claim c1: value mismatch"),
        )
        assert r.valid is False
        assert len(r.errors) == 2
