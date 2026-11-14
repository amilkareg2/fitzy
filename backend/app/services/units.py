"""Weight unit handling.

Weights are stored canonically in kilograms (``weight_kg``) together with the unit the user
entered (``entered_unit``), so a set typed as 225 lb is always shown back as 225 lb even though
analytics run on kg. All arithmetic uses Decimal to avoid float drift.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

KG_PER_LB = Decimal("0.45359237")  # exact, by international definition
KG_STORAGE_PLACES = Decimal("0.0001")  # matches Numeric(9, 4) on workout_set.weight_kg
DISPLAY_PLACES = Decimal("0.01")

type Number = Decimal | int | float | str


class WeightUnit(StrEnum):
    KG = "kg"
    LB = "lb"


def _dec(value: Number) -> Decimal:
    # str() first so floats like 102.5 do not drag in binary noise.
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _unit(unit: str) -> WeightUnit:
    try:
        return WeightUnit(unit.lower())
    except ValueError:
        raise ValueError(f"unknown weight unit {unit!r}; expected 'kg' or 'lb'") from None


def to_kg(value: Number, unit: str) -> Decimal:
    """Convert ``value`` in ``unit`` to kilograms, rounded to storage precision."""
    amount = _dec(value)
    kg = amount if _unit(unit) is WeightUnit.KG else amount * KG_PER_LB
    return kg.quantize(KG_STORAGE_PLACES, rounding=ROUND_HALF_UP)


def from_kg(weight_kg: Number, unit: str, places: Decimal = DISPLAY_PLACES) -> Decimal:
    """Convert kilograms to ``unit`` for display, rounded to ``places``."""
    kg = _dec(weight_kg)
    value = kg if _unit(unit) is WeightUnit.KG else kg / KG_PER_LB
    return value.quantize(places, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class StoredWeight:
    """What gets written to the database for a user-entered weight."""

    weight_kg: Decimal
    entered_unit: WeightUnit


def normalize_weight(value: Number, unit: str) -> StoredWeight:
    """Turn a user-entered weight into its stored form, keeping the entered unit."""
    if _dec(value) < 0:
        raise ValueError("weight cannot be negative")
    return StoredWeight(weight_kg=to_kg(value, unit), entered_unit=_unit(unit))


def display_weight(weight_kg: Number, entered_unit: str) -> Decimal:
    """Weight as the user entered it, e.g. 102.0582 kg stored with 'lb' -> Decimal('225.00')."""
    return from_kg(weight_kg, entered_unit)
