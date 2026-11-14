from decimal import Decimal

import pytest

from app.services.units import (
    KG_PER_LB,
    WeightUnit,
    display_weight,
    from_kg,
    normalize_weight,
    to_kg,
)


def test_kg_is_identity() -> None:
    assert to_kg(100, "kg") == Decimal("100.0000")
    assert from_kg(Decimal("100"), "kg") == Decimal("100.00")


def test_lb_to_kg_uses_exact_factor() -> None:
    assert Decimal("0.45359237") == KG_PER_LB
    assert to_kg(225, "lb") == Decimal("102.0583")
    assert to_kg("45", "LB") == Decimal("20.4117")


@pytest.mark.parametrize("lb", ["45", "135", "225", "315", "2.5", "102.5", "1000"])
def test_lb_round_trips_exactly(lb: str) -> None:
    stored = normalize_weight(lb, "lb")
    assert stored.entered_unit is WeightUnit.LB
    assert display_weight(stored.weight_kg, stored.entered_unit) == Decimal(lb).quantize(
        Decimal("0.01")
    )


def test_kg_round_trips_exactly() -> None:
    stored = normalize_weight(102.5, "kg")
    assert stored == normalize_weight(Decimal("102.5"), "kg")
    assert stored.weight_kg == Decimal("102.5000")
    assert display_weight(stored.weight_kg, "kg") == Decimal("102.50")


def test_float_input_does_not_leak_binary_noise() -> None:
    assert to_kg(0.1 + 0.2, "kg") == Decimal("0.3000")


def test_rejects_unknown_unit_and_negative_weight() -> None:
    with pytest.raises(ValueError, match="unknown weight unit"):
        to_kg(10, "stone")
    with pytest.raises(ValueError, match="negative"):
        normalize_weight(-5, "kg")
