from __future__ import annotations

from datetime import UTC, datetime

from app.models.cash_register import DENOMINATION_FIELDS, CashRegister
from app.models.cash_session import CashExpense, CashExpenseKind, CashSession
from app.services.cash_session import (
    closing_total_cents,
    counts_from,
    expense_total_cents,
    expenses_total_cents,
    opening_total_cents,
)


def _expense(kind: CashExpenseKind, quantity: int, unit_price_cents: int) -> CashExpense:
    return CashExpense(
        kind=kind,
        name="Frais",
        quantity=quantity,
        unit_price_cents=unit_price_cents,
    )


def _counts(**overrides: int) -> dict[str, int]:
    """Every denomination at zero, the way the database defaults them."""

    counts = dict.fromkeys(DENOMINATION_FIELDS, 0)
    counts.update(overrides)
    return counts


def test_counts_are_read_from_every_denomination() -> None:
    cash_register = CashRegister(name="Caisse", **_counts(coins_1_euro=3, notes_50_euro=1))

    counts = counts_from(cash_register)

    assert set(counts) == set(DENOMINATION_FIELDS)
    assert counts["coins_1_euro"] == 3
    assert counts["notes_50_euro"] == 1
    assert counts["coins_1_cent"] == 0


def test_the_closing_columns_are_read_with_their_prefix() -> None:
    opening = {f"closed_{field}": value for field, value in _counts(coins_1_euro=2).items()}
    session = CashSession(session_date=None, **opening)

    counts = counts_from(session, prefix="closed_")

    assert counts["coins_1_euro"] == 2
    assert counts["notes_50_euro"] == 0


def test_an_expense_line_totals_quantity_times_unit_price() -> None:
    expense = _expense(CashExpenseKind.PROFESSIONAL, quantity=3, unit_price_cents=250)

    assert expense_total_cents(expense) == 750


def test_expenses_are_summed_per_kind() -> None:
    expenses = [
        _expense(CashExpenseKind.PROFESSIONAL, 2, 100),
        _expense(CashExpenseKind.PERSONAL, 1, 500),
        _expense(CashExpenseKind.PROFESSIONAL, 1, 50),
    ]

    assert expenses_total_cents(expenses) == 750
    assert expenses_total_cents(expenses, kind=CashExpenseKind.PROFESSIONAL) == 250
    assert expenses_total_cents(expenses, kind=CashExpenseKind.PERSONAL) == 500


def test_totals_are_computed_from_both_counts_of_a_session() -> None:
    session = CashSession(
        session_date=None,
        closed_at=datetime.now(UTC),
        **_counts(coins_2_euro=2, notes_10_euro=1),
        **{f"closed_{field}": value for field, value in _counts(coins_1_euro=4).items()},
    )

    assert opening_total_cents(session) == 1400
    # The register was recounted: the closing total ignores the opening float.
    assert closing_total_cents(session) == 400


def test_an_open_session_has_no_closing_total() -> None:
    session = CashSession(session_date=None, **_counts(coins_1_cent=7))

    assert closing_total_cents(session) is None
