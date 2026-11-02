from decimal import Decimal

import pytest

from app.services.e1rm import epley


def test_epley_formula() -> None:
    assert epley(100, 5) == pytest.approx(116.6667, abs=1e-4)
    assert epley(Decimal("80"), 10) == pytest.approx(106.6667, abs=1e-4)
    assert epley(60, 12) == pytest.approx(84.0)


def test_single_rep_is_the_weight() -> None:
    assert epley(140, 1) == 140.0


@pytest.mark.parametrize("reps", [0, -1, 13, 20])
def test_reps_outside_reliable_range_return_none(reps: int) -> None:
    assert epley(100, reps) is None


@pytest.mark.parametrize("weight", [0, -10])
def test_non_positive_weight_returns_none(weight: float) -> None:
    assert epley(weight, 5) is None
