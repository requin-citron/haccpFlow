from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from jinja2 import StrictUndefined, meta
from jinja2.exceptions import SecurityError, TemplateError, TemplateSyntaxError
from jinja2.sandbox import SandboxedEnvironment
from markupsafe import Markup

from app.config import Settings
from app.core.errors import ApiError
from app.models.template_variable import (
    TemplateVariable,
    TemplateVariableKind,
    TemplateVariableValueType,
)
from app.schemas.template_variable import ProductRow
from app.services.storage import storage_path
from app.services.template_variables import parse_product_rows, validate_value

MAX_RENDERED_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class CompileAsset:
    filename: str
    path: Path


_LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}
_LATEX_SPECIAL = re.compile(r"[\\&%$#_{}~^]")


def escape_latex(value: str) -> str:
    """Escape the characters that would change a LaTeX document's structure."""

    return _LATEX_SPECIAL.sub(lambda match: _LATEX_ESCAPES[match.group(0)], value)


def latex_finalize(value: Any) -> Any:
    """Escape text coming from a variable, keeping ``|safe`` as an opt-out."""

    if isinstance(value, str) and not isinstance(value, Markup):
        return escape_latex(value)
    return value


def format_euro(value: object) -> str:
    """French euro formatting used inside LaTeX: 3.95 -> €3,95."""

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    formatted = f"{amount:,.2f}".replace(",", " ").replace(".", ",")
    return f"€{formatted}"


_ENVIRONMENT = SandboxedEnvironment(
    undefined=StrictUndefined,
    autoescape=False,
    finalize=latex_finalize,
    keep_trailing_newline=True,
    # LaTeX uses "{%" and "{{" in ordinary macro definitions. Keep Jinja
    # delimiters distinct so those constructs stay literal LaTeX.
    variable_start_string="<<",
    variable_end_string=">>",
    block_start_string="<%",
    block_end_string="%>",
    comment_start_string="<#",
    comment_end_string="#>",
)
_ENVIRONMENT.filters["euro"] = format_euro


def validate_template_syntax(source: str) -> None:
    try:
        _ENVIRONMENT.parse(source)
    except TemplateSyntaxError as exc:
        line = ""
        lines = source.splitlines()
        if 1 <= exc.lineno <= len(lines):
            line = lines[exc.lineno - 1].strip()
        snippet = f" — {line[:160]}" if line else ""
        raise ApiError(
            422,
            "template_syntax_error",
            f"Jinja syntax error at line {exc.lineno}: {exc.message}{snippet}",
        ) from exc


def used_variable_names(source: str) -> set[str]:
    """Names referenced by the template, ignoring names defined in loops."""

    try:
        ast = _ENVIRONMENT.parse(source)
    except TemplateSyntaxError:
        return set()
    return set(meta.find_undeclared_variables(ast))


def _convert(raw_value: str, value_type: TemplateVariableValueType) -> object:
    if value_type is TemplateVariableValueType.TEXT:
        return raw_value
    if value_type is TemplateVariableValueType.NUMBER:
        return Decimal(raw_value)
    return date.fromisoformat(raw_value)


def _snapshot_value(raw_value: str, value_type: TemplateVariableValueType) -> str:
    if value_type is TemplateVariableValueType.TEXT:
        return raw_value
    if value_type is TemplateVariableValueType.NUMBER:
        return str(Decimal(raw_value))
    return date.fromisoformat(raw_value).isoformat()


def resolve_variables(
    variables: list[TemplateVariable],
    provided: dict[str, str | list[ProductRow]],
) -> tuple[dict[str, object], dict[str, object]]:
    """Build the Jinja context and the audit snapshot for one generation."""

    by_name = {variable.name: variable for variable in variables}
    unknown = sorted(set(provided) - set(by_name))
    if unknown:
        raise ApiError(
            422,
            "template_values_unknown",
            "Unknown template values were provided",
            context={"unknown": unknown},
        )

    overridden_static = sorted(
        name for name in provided if by_name[name].kind is TemplateVariableKind.STATIC
    )
    if overridden_static:
        raise ApiError(
            422,
            "template_values_static",
            "Static variables cannot be overridden at generation time",
            context={"names": overridden_static},
        )

    missing: list[str] = []
    context: dict[str, object] = {}
    snapshot: dict[str, object] = {}
    for variable in variables:
        if variable.value_type is TemplateVariableValueType.IMAGE:
            if variable.asset is None:
                raise ApiError(
                    422,
                    "template_image_missing",
                    "An image variable has no image",
                    context={"variable": variable.name},
                )
            context[variable.name] = Markup(variable.asset.storage_key)
            snapshot[variable.name] = {
                "filename": variable.asset.original_filename,
                "sha256": variable.asset.sha256,
            }
            continue

        if variable.value_type is TemplateVariableValueType.PRODUCTS:
            if variable.kind is TemplateVariableKind.STATIC:
                raw_rows = parse_product_rows(variable.value)
                rows_json = validate_value(
                    raw_rows,
                    variable.value_type,
                    required=True,
                )
            elif variable.name in provided:
                rows_json = validate_value(
                    provided[variable.name],
                    variable.value_type,
                    required=True,
                )
            else:
                raw_rows = parse_product_rows(variable.value)
                rows_json = validate_value(
                    raw_rows,
                    variable.value_type,
                    required=False,
                )

            if rows_json is None:
                missing.append(variable.name)
                continue

            rows = json.loads(rows_json)
            context[variable.name] = [
                {
                    "designation": row["designation"],
                    "pots": row["pots"],
                    "prix": Decimal(row["prix"]),
                }
                for row in rows
            ]
            snapshot[variable.name] = rows
            continue

        if variable.kind is TemplateVariableKind.STATIC:
            raw_value = validate_value(
                variable.value,
                variable.value_type,
                required=True,
            )
        elif variable.name in provided:
            raw_value = validate_value(
                provided[variable.name],
                variable.value_type,
                required=True,
            )
        else:
            raw_value = validate_value(
                variable.value,
                variable.value_type,
                required=False,
            )

        if raw_value is None:
            missing.append(variable.name)
            continue

        context[variable.name] = _convert(raw_value, variable.value_type)
        snapshot[variable.name] = _snapshot_value(raw_value, variable.value_type)

    if missing:
        raise ApiError(
            422,
            "template_values_missing",
            "Required template values are missing",
            context={"missing": missing},
        )
    return context, snapshot


def collect_assets(
    variables: list[TemplateVariable],
    settings: Settings,
) -> list[CompileAsset]:
    assets: list[CompileAsset] = []
    for variable in variables:
        if variable.value_type is not TemplateVariableValueType.IMAGE:
            continue
        if variable.asset is None:
            raise ApiError(
                422,
                "template_image_missing",
                "An image variable has no image",
                context={"variable": variable.name},
            )
        path = storage_path(
            settings.template_storage_dir / "assets",
            variable.asset.storage_key,
        )
        if not path.is_file():
            raise ApiError(
                422,
                "template_image_missing",
                "The image file is missing from storage",
                context={"variable": variable.name},
            )
        assets.append(CompileAsset(filename=variable.asset.storage_key, path=path))
    return assets


def render_source(
    source: str,
    variables: list[TemplateVariable],
    provided: dict[str, str | list[ProductRow]],
) -> tuple[str, dict[str, object]]:
    """Render the template and return the source plus the values snapshot."""

    context, snapshot = resolve_variables(variables, provided)
    try:
        rendered = _ENVIRONMENT.from_string(source).render(**context)
    except SecurityError as exc:
        raise ApiError(
            422,
            "template_render_failed",
            "The template attempted to access a forbidden value",
        ) from exc
    except TemplateError as exc:
        raise ApiError(
            422,
            "template_render_failed",
            f"The template could not be rendered: {exc}",
        ) from exc

    if len(rendered.encode("utf-8")) > MAX_RENDERED_BYTES:
        raise ApiError(
            422,
            "template_render_too_large",
            "The rendered template is too large",
        )
    return rendered, snapshot
