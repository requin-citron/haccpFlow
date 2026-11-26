from __future__ import annotations

from app.models.cash_register import DENOMINATIONS, CashRegister, CashRegisterKind
from app.services.cash_register import (
    cash_register_has_denomination_counts,
    compute_total_cents,
    kind_uses_denominations,
)


def test_an_empty_count_totals_zero() -> None:
    assert compute_total_cents({}) == 0


def test_coins_and_notes_are_summed_in_cents() -> None:
    counts = {
        "coins_1_cent": 4,
        "coins_20_cent": 3,
        "coins_1_euro": 3,
        "coins_50_cent": 2,
        "notes_5_euro": 1,
    }

    # 4 + 60 + 300 + 100 + 500
    assert compute_total_cents(counts) == 964


def test_the_full_slot_of_every_denomination() -> None:
    counts = {field: 1 for field, _ in DENOMINATIONS}

    # 1 + 2 + 5 + 10 + 20 + 50 + 100 + 200 + 500 + 1000 + 2000 + 5000
    assert compute_total_cents(counts) == 8888


def test_a_denomination_outside_the_list_is_ignored() -> None:
    assert compute_total_cents({"coins_1_euro": 1, "notes_100_euro": 5}) == 100


def test_only_cash_registers_use_denomination_counts() -> None:
    assert kind_uses_denominations(CashRegisterKind.CASH) is True
    assert kind_uses_denominations(CashRegisterKind.CHEQUE) is False
    assert kind_uses_denominations(CashRegisterKind.CARD) is False


def test_denomination_counts_are_detected_on_a_register() -> None:
    empty = CashRegister(
        name="Cartes",
        kind=CashRegisterKind.CARD,
        **dict.fromkeys((field for field, _ in DENOMINATIONS), 0),
    )
    assert cash_register_has_denomination_counts(empty) is False

    empty.coins_1_euro = 1
    assert cash_register_has_denomination_counts(empty) is True
