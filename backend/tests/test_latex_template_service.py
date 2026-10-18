from __future__ import annotations

import pytest

from app.core.errors import ApiError
from app.services.latex_template import (
    decode_template,
    name_key,
    normalize_name,
    sanitize_filename,
    validate_extension,
)


def _error_code(callable_) -> str:
    with pytest.raises(ApiError) as exc_info:
        callable_()
    return exc_info.value.code


def test_sanitize_filename_keeps_the_basename() -> None:
    assert sanitize_filename("../../evil.tex") == "evil.tex"
    assert sanitize_filename("C:\\fakepath\\modele.tex") == "modele.tex"
    assert sanitize_filename("  modele.tex  ") == "modele.tex"


def test_sanitize_filename_rejects_missing_names() -> None:
    assert _error_code(lambda: sanitize_filename(None)) == "template_filename_invalid"
    assert _error_code(lambda: sanitize_filename("..")) == "template_filename_invalid"


def test_only_tex_files_are_allowed() -> None:
    validate_extension("modele.tex")
    validate_extension("MODELE.TEX")
    assert _error_code(lambda: validate_extension("modele.txt")) == "template_type_not_allowed"


def test_name_falls_back_to_the_file_stem() -> None:
    assert normalize_name("", "bon-de-livraison.tex") == "bon-de-livraison"
    assert normalize_name("   ", "modele.tex") == "modele"


def test_name_whitespace_is_collapsed() -> None:
    assert normalize_name("  Modele   principal  ", "x.tex") == "Modele principal"


def test_name_is_limited_to_120_characters() -> None:
    assert _error_code(lambda: normalize_name("x" * 121, "x.tex")) == "template_name_invalid"
    assert normalize_name("x" * 120, "x.tex") == "x" * 120


def test_name_key_is_case_insensitive() -> None:
    assert name_key("Modele Principal") == name_key("modele principal")


def test_utf8_bom_is_removed() -> None:
    source = b"\\documentclass{article}\n"
    assert decode_template(b"\xef\xbb\xbf" + source) == source.decode()


def test_invalid_encoding_is_rejected() -> None:
    assert _error_code(lambda: decode_template(b"\xff\xfe")) == "template_invalid_encoding"


def test_binary_control_characters_are_rejected() -> None:
    assert _error_code(lambda: decode_template(b"abc\x00def")) == "template_invalid_content"


def test_blank_templates_are_rejected() -> None:
    assert _error_code(lambda: decode_template(b" \n\t")) == "template_empty"
