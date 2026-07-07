from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Claim:
    id: str
    metric: str
    value: float | str
    source: str
    source_rows: tuple = ()
    computation: str = ""


@dataclass(frozen=True)
class ClaimsLedger:
    claims: tuple[Claim, ...] = ()
    metadata: dict = field(default_factory=dict)

    def by_id(self) -> dict[str, Claim]:
        return {c.id: c for c in self.claims}

    def values(self) -> list[float | str]:
        return [c.value for c in self.claims]

    def merge(self, other: ClaimsLedger) -> ClaimsLedger:
        return ClaimsLedger(
            claims=self.claims + other.claims,
            metadata={**self.metadata, **other.metadata},
        )


@dataclass
class ClaimsRegistry:
    _claims: list[Claim] = field(default_factory=list)

    def add(self, claim: Claim) -> None:
        self._claims.append(claim)

    def to_ledger(self) -> ClaimsLedger:
        return ClaimsLedger(claims=tuple(self._claims))

    def reset(self) -> None:
        self._claims.clear()

    @property
    def count(self) -> int:
        return len(self._claims)


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: tuple = ()
    truth_labels: dict = field(default_factory=dict)
