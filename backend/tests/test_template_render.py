from __future__ import annotations

import json
from decimal import Decimal

import pytest

from app.core.errors import ApiError
from app.models.template_variable import (
    TemplateVariable,
    TemplateVariableAsset,
    TemplateVariableKind,
    TemplateVariableValueType,
)
from app.schemas.template_variable import ProductRow
from app.services.template_render import (
    escape_latex,
    format_euro,
    render_source,
    used_variable_names,
    validate_template_syntax,
)


def _variable(
    name: str,
    kind: TemplateVariableKind,
    value_type: TemplateVariableValueType,
    value: str | None,
) -> TemplateVariable:
    return TemplateVariable(
        name=name,
        label=name,
        kind=kind,
        value_type=value_type,
        value=value,
    )


def test_latex_special_characters_are_escaped() -> None:
    assert escape_latex("A & B_%$#{}~^\\") == (
        r"A \& B\_\%\$\#\{\}\textasciitilde{}\textasciicircum{}\textbackslash{}"
    )


def test_static_and_local_values_are_rendered_and_escaped() -> None:
    variables = [
        _variable("company", TemplateVariableKind.STATIC, TemplateVariableValueType.TEXT, "A & B"),
        _variable("client", TemplateVariableKind.LOCAL, TemplateVariableValueType.TEXT, None),
    ]

    source = "Company: << company >> / Client: << client >>"
    rendered, snapshot = render_source(source, variables, {"client": "Dupont & Fils"})

    assert rendered == r"Company: A \& B / Client: Dupont \& Fils"
    assert snapshot == {"company": "A & B", "client": "Dupont & Fils"}


def test_local_default_is_used_when_value_is_absent() -> None:
    variables = [
        _variable(
            "amount",
            TemplateVariableKind.LOCAL,
            TemplateVariableValueType.NUMBER,
            "3,95",
        )
    ]

    rendered, snapshot = render_source("<< amount >>", variables, {})

    assert rendered == "3.95"
    assert snapshot == {"amount": "3.95"}


def test_dates_render_from_iso_and_can_be_formatted() -> None:
    variables = [
        _variable(
            "delivery_date",
            TemplateVariableKind.LOCAL,
            TemplateVariableValueType.DATE,
            None,
        )
    ]

    rendered, _ = render_source(
        "<< delivery_date.strftime('%d/%m/%Y') >>",
        variables,
        {"delivery_date": "2026-08-22"},
    )

    assert rendered == "22/08/2026"


def test_jinja_conditions_and_loops_are_available() -> None:
    variables = [
        _variable("items", TemplateVariableKind.LOCAL, TemplateVariableValueType.TEXT, "x"),
    ]
    source = "<% if items %><% for _ in range(3) %>ok<% endfor %><% endif %>"

    rendered, _ = render_source(source, variables, {"items": "x"})

    assert rendered == "okokok"


def test_safe_filter_bypasses_latex_escaping() -> None:
    variables = [
        _variable("value", TemplateVariableKind.LOCAL, TemplateVariableValueType.TEXT, None)
    ]

    rendered, _ = render_source("<< value|safe >>", variables, {"value": r"\textbf{x}"})

    assert rendered == r"\textbf{x}"


def test_missing_local_value_is_reported() -> None:
    variables = [
        _variable("client", TemplateVariableKind.LOCAL, TemplateVariableValueType.TEXT, None)
    ]

    with pytest.raises(ApiError) as exc_info:
        render_source("<< client >>", variables, {})

    assert exc_info.value.code == "template_values_missing"
    assert exc_info.value.context == {"missing": ["client"]}


def test_unknown_value_is_rejected() -> None:
    with pytest.raises(ApiError) as exc_info:
        render_source("x", [], {"extra": "value"})

    assert exc_info.value.code == "template_values_unknown"


def test_static_value_cannot_be_overridden() -> None:
    variables = [
        _variable("company", TemplateVariableKind.STATIC, TemplateVariableValueType.TEXT, "La LEGU")
    ]

    with pytest.raises(ApiError) as exc_info:
        render_source("<< company >>", variables, {"company": "Other"})

    assert exc_info.value.code == "template_values_static"


def test_sandbox_blocks_attribute_access() -> None:
    with pytest.raises(ApiError) as exc_info:
        render_source("<< ''.__class__ >>", [], {})

    assert exc_info.value.code == "template_render_failed"


def test_used_variables_ignore_loop_locals() -> None:
    used = used_variable_names("<% for item in items %> << item.name >> << other >> <% endfor %>")

    assert used == {"items", "other"}


def test_syntax_errors_are_reported() -> None:
    with pytest.raises(ApiError) as exc_info:
        validate_template_syntax("<% if %>")

    assert exc_info.value.code == "template_syntax_error"


def test_euro_filter_formats_french_amounts() -> None:
    assert format_euro(Decimal("3.95")) == "€3,95"
    assert format_euro(Decimal("1234.5")) == "€1 234,50"


def test_product_rows_render_and_totals_are_computed() -> None:
    rows = [
        {"designation": "Bocal & co", "pots": 10, "prix": "3.95"},
        {"designation": "Autre", "pots": 1, "prix": "1.50"},
    ]
    variables = [
        _variable(
            "lignes",
            TemplateVariableKind.LOCAL,
            TemplateVariableValueType.PRODUCTS,
            json.dumps(rows),
        )
    ]
    source = (
        "<% set totals = namespace(pots=0, montant=0) %>"
        "<% for ligne in lignes %>"
        "<% set totals.pots = totals.pots + ligne.pots %>"
        "<% set totals.montant = totals.montant + (ligne.pots * ligne.prix) %>"
        "[<< ligne.designation >>:<< ligne.pots >>:<< ligne.prix|euro >>]"
        "<% endfor %>"
        "|<< totals.pots >>|<< totals.montant|euro >>"
    )

    rendered, snapshot = render_source(source, variables, {})

    assert rendered == r"[Bocal \& co:10:€3,95][Autre:1:€1,50]|11|€41,00"
    assert snapshot["lignes"] == [
        {"designation": "Bocal & co", "pots": 10, "prix": "3.95"},
        {"designation": "Autre", "pots": 1, "prix": "1.50"},
    ]


def test_provided_product_rows_override_the_default() -> None:
    variables = [
        _variable(
            "lignes",
            TemplateVariableKind.LOCAL,
            TemplateVariableValueType.PRODUCTS,
            json.dumps([{"designation": "Défaut", "pots": 1, "prix": "1.00"}]),
        )
    ]

    rendered, snapshot = render_source(
        "<< lignes|length >>",
        variables,
        {"lignes": [ProductRow(designation="Nouveau", pots=2, prix="2,5")]},
    )

    assert rendered == "1"
    assert snapshot["lignes"] == [{"designation": "Nouveau", "pots": 2, "prix": "2.50"}]


def test_static_image_variable_exposes_a_safe_filename() -> None:
    variable = _variable(
        "logo",
        TemplateVariableKind.STATIC,
        TemplateVariableValueType.IMAGE,
        None,
    )
    variable.asset = TemplateVariableAsset(
        storage_key="abc.png",
        original_filename="logo.png",
        content_type="image/png",
        size_bytes=10,
        sha256="digest",
    )

    rendered, snapshot = render_source(r"\includegraphics{<< logo >>}", [variable], {})

    assert rendered == r"\includegraphics{abc.png}"
    assert snapshot["logo"] == {"filename": "logo.png", "sha256": "digest"}


def test_missing_image_asset_is_rejected() -> None:
    variable = _variable(
        "logo",
        TemplateVariableKind.STATIC,
        TemplateVariableValueType.IMAGE,
        None,
    )

    with pytest.raises(ApiError) as exc_info:
        render_source(r"\includegraphics{<< logo >>}", [variable], {})

    assert exc_info.value.code == "template_image_missing"
