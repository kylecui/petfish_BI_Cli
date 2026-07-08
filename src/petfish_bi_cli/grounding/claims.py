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
    allowed_numbers: tuple[float, ...] = ()

    def by_id(self) -> dict[str, Claim]:
        return {c.id: c for c in self.claims}

    def values(self) -> list[float | str]:
        return [c.value for c in self.claims]

    def all_grounded_numbers(self) -> set[float]:
        nums: set[float] = set()
        for c in self.claims:
            if isinstance(c.value, (int, float)):
                nums.add(float(c.value))
        for n in self.allowed_numbers:
            nums.add(float(n))
        return nums

    def merge(self, other: ClaimsLedger) -> ClaimsLedger:
        return ClaimsLedger(
            claims=self.claims + other.claims,
            metadata={**self.metadata, **other.metadata},
            allowed_numbers=self.allowed_numbers + other.allowed_numbers,
        )


@dataclass
class ClaimsRegistry:
    _claims: list[Claim] = field(default_factory=list)
    _allowed_numbers: list[float] = field(default_factory=list)

    def add(self, claim: Claim) -> None:
        self._claims.append(claim)

    def add_allowed_number(self, value: float | int) -> None:
        self._allowed_numbers.append(float(value))

    def add_from_metadata(self, metadata: dict) -> None:
        for _key, val in metadata.items():
            if isinstance(val, (int, float)) and val == int(val):
                self.add_allowed_number(float(val))
            elif isinstance(val, dict):
                self.add_from_metadata(val)

    def to_ledger(self) -> ClaimsLedger:
        return ClaimsLedger(
            claims=tuple(self._claims),
            allowed_numbers=tuple(self._allowed_numbers),
        )

    def reset(self) -> None:
        self._claims.clear()
        self._allowed_numbers.clear()

    @property
    def count(self) -> int:
        return len(self._claims)


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: tuple = ()
    truth_labels: dict = field(default_factory=dict)
