from __future__ import annotations

from app.models.cash_register import DENOMINATIONS
from app.services.cash_register import compute_total_cents


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
