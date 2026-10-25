from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Quote:
    usd_min: float
    usd_max: float
    as_of: str
    basis: str

    def __post_init__(self) -> None:
        # Six decimals: float noise must not push 0.28 * 5 past a cap of 1.40.
        object.__setattr__(self, "usd_min", round(self.usd_min, 6))
        object.__setattr__(self, "usd_max", round(self.usd_max, 6))
        if not 0 <= self.usd_min <= self.usd_max:
            raise ValueError(f"bad quote range {self.usd_min}..{self.usd_max}")

    def to_json(self) -> dict:
        return {
            "usdMin": self.usd_min,
            "usdMax": self.usd_max,
            "asOf": self.as_of,
            "basis": self.basis,
        }
