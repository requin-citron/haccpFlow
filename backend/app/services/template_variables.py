from __future__ import annotations

import json
import re
import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import cast

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models.template_variable import (
    TemplateVariable,
    TemplateVariableKind,
    TemplateVariableValueType,
)
from app.schemas.template_variable import ProductRow, TemplateVariableWrite

MAX_TEXT_VALUE_LENGTH = 10_000
MAX_NUMBER_LENGTH = 64
MAX_PRODUCT_ROWS = 100
MAX_PRODUCT_DESIGNATION = 200
MAX_PRODUCT_POTS = 1_000_000
MAX_PRODUCT_PRICE = Decimal("1000000")

#: C0 controls except tab, newline and carriage return.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_VARIABLE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")

#: Jinja keywords and literals cannot be used as variable identifiers.
_JINJA_RESERVED = frozenset(
    {
        "and",
        "as",
        "autoescape",
        "block",
        "break",
        "call",
        "continue",
        "do",
        "elif",
        "else",
        "endautoescape",
        "endblock",
        "endcall",
        "endfilter",
        "endfor",
        "endif",
        "endmacro",
        "endraw",
        "endset",
        "endtrans",
        "endverbatim",
        "extends",
        "false",
        "filter",
        "for",
        "from",
        "if",
        "import",
        "in",
        "include",
        "is",
        "macro",
        "none",
        "not",
        "or",
        "pluralize",
        "raw",
        "set",
        "trans",
        "true",
        "verbatim",
        "while",
        "with",
        "without",
    }
)


def _invalid(field: str, message: str) -> ApiError:
    return ApiError(422, "template_variable_invalid", message, context={"field": field})


def validate_variable_name(raw_name: str) -> str:
    name = raw_name.strip()
    if not _VARIABLE_NAME.fullmatch(name) or name.lower() in _JINJA_RESERVED:
        raise _invalid(
            "name",
            "The variable name must be a Jinja identifier (letters, digits, underscore)",
        )
    return name


def validate_label(raw_label: str) -> str:
    label = " ".join(raw_label.split())
    if not label:
        raise _invalid("label", "The label is required")
    if _CONTROL_CHARS.search(raw_label):
        raise _invalid("label", "The label contains invalid characters")
    return label


def validate_description(raw_description: str | None) -> str | None:
    if raw_description is None:
        return None
    if _CONTROL_CHARS.search(raw_description):
        raise _invalid("description", "The description contains invalid characters")
    description = raw_description.strip()
    return description or None


def validate_value(
    raw_value: str | Sequence[ProductRow | dict[str, object]] | None,
    value_type: TemplateVariableValueType,
    *,
    required: bool,
) -> str | None:
    """Validate and normalize a static value or a local default."""

    if raw_value is None:
        if required:
            raise ApiError(
                422,
                "template_value_invalid",
                "A static variable requires a value",
                context={"field": "value"},
            )
        return None

    if value_type is TemplateVariableValueType.PRODUCTS:
        if isinstance(raw_value, str):
            raise ApiError(
                422,
                "template_value_invalid",
                "The value must be a list of product rows",
                context={"field": "value"},
            )
        if not isinstance(raw_value, Sequence):
            raise ApiError(
                422,
                "template_value_invalid",
                "The value must be a list of product rows",
                context={"field": "value"},
            )
        rows = _normalize_product_rows(
            cast("Sequence[ProductRow | dict[str, object]]", raw_value)
        )
        return json.dumps(rows, ensure_ascii=False, separators=(",", ":"))

    if not isinstance(raw_value, str):
        raise ApiError(
            422,
            "template_value_invalid",
            "The value must be a string",
            context={"field": "value"},
        )

    if _CONTROL_CHARS.search(raw_value):
        raise ApiError(
            422,
            "template_value_invalid",
            "The value contains invalid control characters",
            context={"field": "value"},
        )

    if value_type is TemplateVariableValueType.TEXT:
        if len(raw_value) > MAX_TEXT_VALUE_LENGTH:
            raise ApiError(
                422,
                "template_value_invalid",
                f"The value must be at most {MAX_TEXT_VALUE_LENGTH} characters",
                context={"field": "value"},
            )
        return raw_value

    stripped = raw_value.strip()
    if not stripped:
        raise ApiError(
            422,
            "template_value_invalid",
            "The value must not be blank",
            context={"field": "value"},
        )

    if value_type is TemplateVariableValueType.NUMBER:
        if len(stripped) > MAX_NUMBER_LENGTH:
            raise ApiError(
                422,
                "template_value_invalid",
                "The number is too long",
                context={"field": "value"},
            )
        normalized = stripped.replace(",", ".")
        try:
            number = Decimal(normalized)
        except InvalidOperation as exc:
            raise ApiError(
                422,
                "template_value_invalid",
                "The value must be a number",
                context={"field": "value"},
            ) from exc
        if not number.is_finite():
            raise ApiError(
                422,
                "template_value_invalid",
                "The number must be finite",
                context={"field": "value"},
            )
        return normalized

    try:
        parsed = date.fromisoformat(stripped)
    except ValueError as exc:
        raise ApiError(
            422,
            "template_value_invalid",
            "The value must be an ISO date (YYYY-MM-DD)",
            context={"field": "value"},
        ) from exc
    return parsed.isoformat()


def _normalize_product_rows(
    rows: Sequence[ProductRow | dict[str, object]],
) -> list[dict[str, object]]:
    if len(rows) > MAX_PRODUCT_ROWS:
        raise ApiError(
            422,
            "template_value_invalid",
            f"A products variable may contain at most {MAX_PRODUCT_ROWS} rows",
            context={"field": "value"},
        )

    normalized: list[dict[str, object]] = []
    for index, raw_row in enumerate(rows):
        try:
            row = (
                raw_row
                if isinstance(raw_row, ProductRow)
                else ProductRow.model_validate(raw_row)
            )
        except ValidationError as exc:
            raise ApiError(
                422,
                "template_value_invalid",
                "Each product row is invalid",
                context={"field": "value", "row": index},
            ) from exc
        designation = row.designation.strip()
        if not designation or _CONTROL_CHARS.search(row.designation):
            raise ApiError(
                422,
                "template_value_invalid",
                "Each product row needs a valid designation",
                context={"field": "value", "row": index},
            )
        if len(designation) > MAX_PRODUCT_DESIGNATION:
            raise ApiError(
                422,
                "template_value_invalid",
                f"Product designations must be at most {MAX_PRODUCT_DESIGNATION} characters",
                context={"field": "value", "row": index},
            )
        if not 0 <= row.pots <= MAX_PRODUCT_POTS:
            raise ApiError(
                422,
                "template_value_invalid",
                "Product quantities must be positive integers",
                context={"field": "value", "row": index},
            )

        price_text = row.prix.strip().replace(",", ".")
        try:
            price = Decimal(price_text)
        except InvalidOperation as exc:
            raise ApiError(
                422,
                "template_value_invalid",
                "Product prices must be numbers",
                context={"field": "value", "row": index},
            ) from exc
        if not price.is_finite() or price < 0 or price > MAX_PRODUCT_PRICE:
            raise ApiError(
                422,
                "template_value_invalid",
                "Product prices must be positive and finite",
                context={"field": "value", "row": index},
            )
        normalized.append(
            {
                "designation": designation,
                "pots": row.pots,
                "prix": str(price.quantize(Decimal("0.01"))),
            }
        )
    return normalized


def parse_product_rows(value: str | None) -> list[dict[str, object]] | None:
    """Read the JSON stored in a products variable; malformed data is rejected."""

    if value is None:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ApiError(
            422,
            "template_value_invalid",
            "The products value is not valid JSON",
        ) from exc
    if not isinstance(parsed, list):
        raise ApiError(
            422,
            "template_value_invalid",
            "The products value must be a list",
        )
    return parsed


def serialize_variable_value(
    variable: TemplateVariable,
) -> str | list[dict[str, object]] | None:
    """Value returned by the API: a list for products, a string otherwise."""

    if variable.value_type is TemplateVariableValueType.PRODUCTS:
        return parse_product_rows(variable.value)
    return variable.value


def _validated_fields(payload: TemplateVariableWrite) -> dict[str, object]:
    return {
        "name": validate_variable_name(payload.name),
        "label": validate_label(payload.label),
        "description": validate_description(payload.description),
        "kind": payload.kind,
        "value_type": payload.value_type,
        "value": validate_value(
            payload.value,
            payload.value_type,
            required=payload.kind is TemplateVariableKind.STATIC,
        ),
    }


async def list_variables(
    db: AsyncSession,
    template_id: uuid.UUID,
) -> list[TemplateVariable]:
    result = await db.scalars(
        select(TemplateVariable)
        .where(TemplateVariable.template_id == template_id)
        .order_by(TemplateVariable.name)
    )
    return list(result)


async def _name_is_taken(
    db: AsyncSession,
    template_id: uuid.UUID,
    name: str,
    *,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    query = select(TemplateVariable.id).where(
        TemplateVariable.template_id == template_id,
        TemplateVariable.name == name,
    )
    if exclude_id is not None:
        query = query.where(TemplateVariable.id != exclude_id)
    return await db.scalar(query) is not None


async def create_variable(
    db: AsyncSession,
    template_id: uuid.UUID,
    payload: TemplateVariableWrite,
) -> TemplateVariable:
    fields = _validated_fields(payload)
    name = str(fields["name"])
    if await _name_is_taken(db, template_id, name):
        raise ApiError(
            409,
            "template_variable_name_taken",
            "A variable with this name already exists on this template",
        )

    variable = TemplateVariable(template_id=template_id, **fields)
    db.add(variable)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ApiError(
            409,
            "template_variable_name_taken",
            "A variable with this name already exists on this template",
        ) from exc

    await db.refresh(variable)
    return variable


async def get_variable(
    db: AsyncSession,
    template_id: uuid.UUID,
    variable_id: uuid.UUID,
) -> TemplateVariable:
    variable = await db.scalar(
        select(TemplateVariable).where(
            TemplateVariable.id == variable_id,
            TemplateVariable.template_id == template_id,
        )
    )
    if variable is None:
        raise ApiError(404, "template_variable_not_found", "Template variable not found")
    return variable


async def update_variable(
    db: AsyncSession,
    template_id: uuid.UUID,
    variable_id: uuid.UUID,
    payload: TemplateVariableWrite,
) -> TemplateVariable:
    variable = await get_variable(db, template_id, variable_id)
    fields = _validated_fields(payload)
    name = str(fields["name"])
    if name != variable.name and await _name_is_taken(
        db,
        template_id,
        name,
        exclude_id=variable_id,
    ):
        raise ApiError(
            409,
            "template_variable_name_taken",
            "A variable with this name already exists on this template",
        )

    for field, value in fields.items():
        setattr(variable, field, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ApiError(
            409,
            "template_variable_name_taken",
            "A variable with this name already exists on this template",
        ) from exc

    await db.refresh(variable)
    return variable


async def delete_variable(
    db: AsyncSession,
    template_id: uuid.UUID,
    variable_id: uuid.UUID,
) -> None:
    variable = await get_variable(db, template_id, variable_id)
    await db.delete(variable)
    await db.commit()
