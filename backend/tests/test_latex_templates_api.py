from __future__ import annotations

import hashlib
import re
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings

TEMPLATES = "/api/v1/templates"
TEX = b"\\documentclass{article}\n\\begin{document}\nBonjour\n\\end{document}\n"
STORAGE_KEY = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.tex$")


@pytest.fixture
def storage_settings(tmp_path: Path) -> Settings:
    return Settings(
        secret_key="unit-test-secret-key",
        database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
        template_storage_dir=tmp_path / "templates",
        template_max_upload_bytes=1024,
        _env_file=None,
    )


@pytest.fixture
def templates_client(
    api_client: TestClient,
    storage_settings: Settings,
) -> Iterator[TestClient]:
    api_client.app.dependency_overrides[get_settings] = lambda: storage_settings
    yield api_client
    api_client.app.dependency_overrides.pop(get_settings, None)


def _stored_files(settings: Settings) -> list[Path]:
    directory = settings.template_storage_dir
    return sorted(directory.iterdir()) if directory.exists() else []


def _upload(
    client: TestClient,
    headers: dict[str, str] | None,
    *,
    name: str | None = None,
    filename: str = "modele.tex",
    content: bytes = TEX,
):
    data = {"name": name} if name is not None else {}
    return client.post(
        TEMPLATES,
        headers=headers,
        data=data,
        files={"file": (filename, content, "text/plain")},
    )


def test_admin_can_upload_list_and_download(
    templates_client: TestClient,
    admin_headers: dict[str, str],
    storage_settings: Settings,
) -> None:
    response = _upload(templates_client, admin_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "modele"
    assert body["original_filename"] == "modele.tex"
    assert body["size_bytes"] == len(TEX)
    assert body["sha256"] == hashlib.sha256(TEX).hexdigest()
    assert body["uploaded_by_email"] == "admin@test.local"

    files = _stored_files(storage_settings)
    assert len(files) == 1
    assert STORAGE_KEY.match(files[0].name)
    assert files[0].read_bytes() == TEX

    listing = templates_client.get(TEMPLATES, headers=admin_headers)
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [body["id"]]

    download = templates_client.get(
        f"{TEMPLATES}/{body['id']}/download",
        headers=admin_headers,
    )
    assert download.status_code == 200
    assert download.content == TEX
    assert "modele.tex" in download.headers["content-disposition"]
    assert download.headers["x-content-type-options"] == "nosniff"


def test_upload_list_and_download_are_admin_only(
    templates_client: TestClient,
    admin_headers: dict[str, str],
    operator_headers: dict[str, str],
) -> None:
    created = _upload(templates_client, admin_headers)
    assert created.status_code == 201
    template_id = created.json()["id"]

    assert _upload(templates_client, operator_headers).status_code == 403
    assert _upload(templates_client, None).status_code == 401
    assert templates_client.get(TEMPLATES, headers=operator_headers).status_code == 403
    assert templates_client.get(TEMPLATES).status_code == 401
    assert (
        templates_client.get(
            f"{TEMPLATES}/{template_id}/download",
            headers=operator_headers,
        ).status_code
        == 403
    )
    assert templates_client.get(f"{TEMPLATES}/{template_id}/download").status_code == 401


def test_duplicate_names_are_rejected_case_insensitively(
    templates_client: TestClient,
    admin_headers: dict[str, str],
    storage_settings: Settings,
) -> None:
    assert _upload(templates_client, admin_headers, name="Modele").status_code == 201

    duplicate = _upload(templates_client, admin_headers, name="modele")

    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "template_name_taken"
    assert len(_stored_files(storage_settings)) == 1


def test_uploaded_filename_never_becomes_a_path(
    templates_client: TestClient,
    admin_headers: dict[str, str],
    storage_settings: Settings,
) -> None:
    response = _upload(templates_client, admin_headers, filename="../../evil.tex")

    assert response.status_code == 201
    assert response.json()["original_filename"] == "evil.tex"
    files = _stored_files(storage_settings)
    assert len(files) == 1
    assert STORAGE_KEY.match(files[0].name)
    assert not (storage_settings.template_storage_dir.parent / "evil.tex").exists()


def test_oversized_files_are_rejected(
    templates_client: TestClient,
    admin_headers: dict[str, str],
    storage_settings: Settings,
) -> None:
    response = _upload(templates_client, admin_headers, content=b"x" * 2048)

    assert response.status_code == 413
    assert response.json()["code"] == "template_too_large"
    assert _stored_files(storage_settings) == []


def test_wrong_extension_is_rejected(
    templates_client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    response = _upload(templates_client, admin_headers, filename="modele.txt")

    assert response.status_code == 415
    assert response.json()["code"] == "template_type_not_allowed"


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (b"", "template_empty"),
        (b"\xff\xfe", "template_invalid_encoding"),
        (b"abc\x00def", "template_invalid_content"),
    ],
)
def test_invalid_content_is_rejected(
    templates_client: TestClient,
    admin_headers: dict[str, str],
    content: bytes,
    code: str,
) -> None:
    response = _upload(templates_client, admin_headers, content=content)

    assert response.status_code == 422
    assert response.json()["code"] == code


def test_name_too_long_is_rejected(
    templates_client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    response = _upload(templates_client, admin_headers, name="x" * 121)

    assert response.status_code == 422
    assert response.json()["code"] == "template_name_invalid"


def test_utf8_bom_is_not_stored(
    templates_client: TestClient,
    admin_headers: dict[str, str],
    storage_settings: Settings,
) -> None:
    response = _upload(templates_client, admin_headers, content=b"\xef\xbb\xbf" + TEX)

    assert response.status_code == 201
    assert response.json()["size_bytes"] == len(TEX)
    assert _stored_files(storage_settings)[0].read_bytes() == TEX


def test_unknown_template_is_not_found(
    templates_client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    response = templates_client.get(
        f"{TEMPLATES}/{uuid.uuid4()}/download",
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "template_not_found"


def test_missing_storage_file_is_reported(
    templates_client: TestClient,
    admin_headers: dict[str, str],
    storage_settings: Settings,
) -> None:
    created = _upload(templates_client, admin_headers)
    _stored_files(storage_settings)[0].unlink()

    response = templates_client.get(
        f"{TEMPLATES}/{created.json()['id']}/download",
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "template_file_missing"
