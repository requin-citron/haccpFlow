from __future__ import annotations

import re
from pathlib import Path

from app.main import create_app

DOC_DIR = Path(__file__).resolve().parents[2] / "doc"


def test_every_openapi_route_is_documented() -> None:
    api_doc = (DOC_DIR / "04-api.md").read_text(encoding="utf-8")
    missing = [path for path in create_app().openapi()["paths"] if path not in api_doc]

    assert missing == []


def test_every_internal_documentation_link_resolves() -> None:
    missing: list[str] = []
    for page in sorted(DOC_DIR.glob("*.md")):
        text = page.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            path = target.split("#", 1)[0]
            if not path or path.startswith(("http://", "https://", "mailto:")):
                continue
            if not (page.parent / path).exists():
                missing.append(f"{page.name}: {target}")

    assert missing == []


def test_the_wiki_index_lists_every_page() -> None:
    index = (DOC_DIR / "README.md").read_text(encoding="utf-8")
    missing = [
        page.name
        for page in sorted(DOC_DIR.glob("*.md"))
        if page.name != "README.md"
        and f"./{page.name}" not in index
        and f"({page.name})" not in index
    ]

    assert missing == []
