from __future__ import annotations

import json

import pytest

from app.core.errors import ApiError
from app.models.template_variable import TemplateVariableValueType
from app.schemas.template_variable import ProductRow
from app.services.template_variables import (
    validate_description,
    validate_label,
    validate_value,
    validate_variable_name,
)


def _error_code(callable_) -> str:
    with pytest.raises(ApiError) as exc_info:
        callable_()
    return exc_info.value.code


def test_valid_identifiers_are_accepted() -> None:
    assert validate_variable_name("client_nom") == "client_nom"
    assert validate_variable_name("Date2") == "Date2"


@pytest.mark.parametrize("name", ["", "2date", "_private", "nom-avec-tiret", "for", "true"])
def test_invalid_identifiers_are_rejected(name: str) -> None:
    assert _error_code(lambda: validate_variable_name(name)) == "template_variable_invalid"


def test_labels_and_descriptions_are_normalized() -> None:
    assert validate_label("  Nom   du client  ") == "Nom du client"
    assert validate_description("  ") is None
    assert _error_code(lambda: validate_label("   ")) == "template_variable_invalid"


def test_text_values_are_kept_as_is() -> None:
    assert validate_value("A & B", TemplateVariableValueType.TEXT, required=True) == "A & B"


def test_number_values_accept_french_decimals() -> None:
    assert validate_value("3,95", TemplateVariableValueType.NUMBER, required=True) == "3.95"
    assert (
        _error_code(lambda: validate_value("abc", TemplateVariableValueType.NUMBER, required=True))
        == "template_value_invalid"
    )


def test_date_values_must_be_iso() -> None:
    assert validate_value("2026-08-22", TemplateVariableValueType.DATE, required=True) == (
        "2026-08-22"
    )
    assert (
        _error_code(
            lambda: validate_value("22/08/2026", TemplateVariableValueType.DATE, required=True)
        )
        == "template_value_invalid"
    )


def test_static_values_are_required_and_local_values_are_optional() -> None:
    assert (
        _error_code(lambda: validate_value(None, TemplateVariableValueType.TEXT, required=True))
        == "template_value_invalid"
    )
    assert validate_value(None, TemplateVariableValueType.TEXT, required=False) is None


def test_product_rows_are_validated_and_normalized() -> None:
    value = validate_value(
        [ProductRow(designation="Bocal", pots=10, prix="3,95")],
        TemplateVariableValueType.PRODUCTS,
        required=True,
    )

    assert json.loads(value) == [{"designation": "Bocal", "pots": 10, "prix": "3.95"}]


def test_empty_product_lists_are_allowed() -> None:
    assert (
        validate_value(
            [],
            TemplateVariableValueType.PRODUCTS,
            required=True,
        )
        == "[]"
    )


@pytest.mark.parametrize(
    "row",
    [
        {"designation": "   ", "pots": 1, "prix": "1"},
        {"designation": "A", "pots": 1, "prix": "abc"},
        {"designation": "A", "pots": -1, "prix": "1"},
        {"designation": "A", "pots": 1, "prix": "NaN"},
    ],
)
def test_invalid_product_rows_are_rejected(row: dict) -> None:
    assert (
        _error_code(
            lambda: validate_value(
                [row],
                TemplateVariableValueType.PRODUCTS,
                required=True,
            )
        )
        == "template_value_invalid"
    )


def test_product_rows_are_limited() -> None:
    rows = [ProductRow(designation="A", pots=1, prix="1")] * 101

    assert (
        _error_code(
            lambda: validate_value(
                rows,
                TemplateVariableValueType.PRODUCTS,
                required=True,
            )
        )
        == "template_value_invalid"
    )


def test_image_variables_do_not_take_text_values() -> None:
    assert (
        validate_value(
            None,
            TemplateVariableValueType.IMAGE,
            required=True,
        )
        is None
    )
    assert (
        _error_code(
            lambda: validate_value(
                "image.png",
                TemplateVariableValueType.IMAGE,
                required=True,
            )
        )
        == "template_value_invalid"
    )
