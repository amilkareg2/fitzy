"""Estimated one-rep max."""

from decimal import Decimal

MAX_RELIABLE_REPS = 12  # rep-max formulas get unreliable beyond ~10-12 reps


def epley(weight: Decimal | float | int, reps: int) -> float | None:
    """Epley estimate: ``weight * (1 + reps / 30)``.

    Returns ``None`` when the estimate is not meaningful: reps outside 1..12 or a non-positive
    weight (bodyweight-only sets carry no load). A single rep returns the weight itself, since a
    performed 1RM is not an estimate (plain Epley would inflate it by 3.3%).
    """
    if reps < 1 or reps > MAX_RELIABLE_REPS:
        return None
    w = float(weight)
    if w <= 0:
        return None
    if reps == 1:
        return w
    return w * (1 + reps / 30)
