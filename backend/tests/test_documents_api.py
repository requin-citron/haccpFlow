from __future__ import annotations

import base64
import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings

pytestmark = pytest.mark.skipif(
    shutil.which("pdflatex") is None,
    reason="pdflatex is required for PDF generation tests",
)

TEMPLATES = "/api/v1/templates"
DOCUMENTS = "/api/v1/documents"
SOURCE = r"""\documentclass{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\begin{document}
Client: << client >>\\
Date: << delivery_date.strftime('%d/%m/%Y') >>\\
Montant: << amount >>\\
Societe: << company >>
\end{document}
"""
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
)


def _upload_template(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str = "Modele",
    source: str = SOURCE,
) -> dict:
    response = client.post(
        TEMPLATES,
        headers=headers,
        data={"name": name},
        files={"file": (f"{name}.tex", source.encode(), "text/plain")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_variable(
    client: TestClient,
    headers: dict[str, str],
    template_id: str,
    *,
    name: str,
    kind: str = "local",
    value_type: str = "text",
    value: str | list[dict] | None = None,
) -> None:
    response = client.post(
        f"{TEMPLATES}/{template_id}/variables",
        headers=headers,
        json={
            "name": name,
            "label": name,
            "kind": kind,
            "value_type": value_type,
            "value": value,
        },
    )
    assert response.status_code == 201, response.text


def _configure_template(
    client: TestClient,
    admin_headers: dict[str, str],
) -> str:
    template = _upload_template(client, admin_headers)
    template_id = template["id"]
    _create_variable(
        client,
        admin_headers,
        template_id,
        name="company",
        kind="static",
        value="Entreprise Test",
    )
    _create_variable(client, admin_headers, template_id, name="client")
    _create_variable(
        client,
        admin_headers,
        template_id,
        name="delivery_date",
        value_type="date",
        value="2026-08-22",
    )
    _create_variable(
        client,
        admin_headers,
        template_id,
        name="amount",
        value_type="number",
        value="3,95",
    )
    return template_id


def test_preview_renders_jinja_with_escaping(
    templates_client: TestClient,
    admin_headers: dict[str, str],
    operator_headers: dict[str, str],
) -> None:
    template_id = _configure_template(templates_client, admin_headers)
    path = f"{TEMPLATES}/{template_id}/preview"

    response = templates_client.post(
        path,
        headers=admin_headers,
        json={"values": {"client": "A & B"}},
    )

    assert response.status_code == 200
    assert r"A \& B" in response.text
    assert "22/08/2026" in response.text
    assert "3.95" in response.text
    assert "Entreprise Test" in response.text
    assert (
        templates_client.post(
            path,
            headers=operator_headers,
            json={"values": {"client": "A & B"}},
        ).status_code
        == 403
    )


def test_operator_can_generate_list_and_download(
    templates_client: TestClient,
    admin_headers: dict[str, str],
    operator_headers: dict[str, str],
    template_settings: Settings,
) -> None:
    template_id = _configure_template(templates_client, admin_headers)

    generated = templates_client.post(
        f"{TEMPLATES}/{template_id}/generate",
        headers=operator_headers,
        json={"values": {"client": "Dupont & Fils"}},
    )

    assert generated.status_code == 201, generated.text
    document = generated.json()
    assert document["template_id"] == template_id
    assert document["generated_by_email"] == "operator@test.local"
    assert document["values"] == {
        "amount": "3.95",
        "client": "Dupont & Fils",
        "company": "Entreprise Test",
        "delivery_date": "2026-08-22",
    }
    assert document["filename"].endswith(".pdf")

    stored = list(template_settings.template_document_storage_dir.iterdir())
    assert len(stored) == 1
    pdf = stored[0].read_bytes()
    assert pdf.startswith(b"%PDF")
    assert document["size_bytes"] == len(pdf)
    assert document["sha256"] == hashlib.sha256(pdf).hexdigest()

    listing = templates_client.get(DOCUMENTS, headers=operator_headers)
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [document["id"]]
    assert templates_client.get(DOCUMENTS, headers=admin_headers).status_code == 200
    assert templates_client.get(DOCUMENTS).status_code == 401

    download = templates_client.get(
        f"{DOCUMENTS}/{document['id']}/download",
        headers=operator_headers,
    )
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF")
    assert download.headers["content-type"] == "application/pdf"
    assert ".pdf" in download.headers["content-disposition"]


def test_missing_unknown_and_invalid_values_are_rejected(
    templates_client: TestClient,
    admin_headers: dict[str, str],
    operator_headers: dict[str, str],
) -> None:
    template_id = _configure_template(templates_client, admin_headers)
    path = f"{TEMPLATES}/{template_id}/generate"

    missing = templates_client.post(path, headers=operator_headers, json={"values": {}})
    assert missing.status_code == 422
    assert missing.json()["code"] == "template_values_missing"
    assert missing.json()["context"] == {"missing": ["client"]}

    unknown = templates_client.post(
        path,
        headers=operator_headers,
        json={"values": {"client": "A", "extra": "B"}},
    )
    assert unknown.status_code == 422
    assert unknown.json()["code"] == "template_values_unknown"

    static = templates_client.post(
        path,
        headers=operator_headers,
        json={"values": {"client": "A", "company": "Autre"}},
    )
    assert static.status_code == 422
    assert static.json()["code"] == "template_values_static"

    invalid_date = templates_client.post(
        path,
        headers=operator_headers,
        json={"values": {"client": "A", "delivery_date": "22/08/2026"}},
    )
    assert invalid_date.status_code == 422
    assert invalid_date.json()["code"] == "template_value_invalid"

    invalid_number = templates_client.post(
        path,
        headers=operator_headers,
        json={"values": {"client": "A", "amount": "beaucoup"}},
    )
    assert invalid_number.status_code == 422
    assert invalid_number.json()["code"] == "template_value_invalid"

    assert templates_client.get(DOCUMENTS, headers=operator_headers).json() == []


def test_compilation_failure_does_not_store_a_document(
    templates_client: TestClient,
    admin_headers: dict[str, str],
    operator_headers: dict[str, str],
    template_settings: Settings,
) -> None:
    template = _upload_template(
        templates_client,
        admin_headers,
        name="Cassee",
        source=r"""\documentclass{article}
\begin{document}
\thiscommanddoesnotexist
\end{document}
""",
    )

    response = templates_client.post(
        f"{TEMPLATES}/{template['id']}/generate",
        headers=operator_headers,
        json={"values": {}},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "template_compilation_failed"
    assert templates_client.get(DOCUMENTS, headers=operator_headers).json() == []
    directory: Path = template_settings.template_document_storage_dir
    assert not directory.exists() or list(directory.iterdir()) == []


def test_missing_document_file_is_reported(
    templates_client: TestClient,
    admin_headers: dict[str, str],
    operator_headers: dict[str, str],
    template_settings: Settings,
) -> None:
    template_id = _configure_template(templates_client, admin_headers)
    document = templates_client.post(
        f"{TEMPLATES}/{template_id}/generate",
        headers=operator_headers,
        json={"values": {"client": "A"}},
    ).json()

    next(template_settings.template_document_storage_dir.iterdir()).unlink()

    response = templates_client.get(
        f"{DOCUMENTS}/{document['id']}/download",
        headers=operator_headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "document_file_missing"


def test_operator_can_generate_with_dynamic_product_rows(
    templates_client: TestClient,
    admin_headers: dict[str, str],
    operator_headers: dict[str, str],
) -> None:
    source = r"""\documentclass{article}
\begin{document}
Client: << client >>\\
<% set totals = namespace(pots=0, montant=0) %>
<% for ligne in lignes_produits %>
<% set totals.pots = totals.pots + ligne.pots %>
<% set totals.montant = totals.montant
   + (ligne.pots * ligne.prix) %>
Ligne: << ligne.designation >> / << ligne.pots >> / << ligne.prix|euro >> /
<< (ligne.pots * ligne.prix)|euro >>\\
<% endfor %>
Total: << totals.pots >> / << totals.montant|euro >>
\end{document}
"""
    template = _upload_template(
        templates_client,
        admin_headers,
        name="Produits",
        source=source,
    )
    template_id = template["id"]
    _create_variable(templates_client, admin_headers, template_id, name="client")
    _create_variable(
        templates_client,
        admin_headers,
        template_id,
        name="lignes_produits",
        value_type="products",
        value=[{"designation": "Défaut", "pots": 1, "prix": "1,00"}],
    )

    rows = [
        {"designation": f"Produit {index}", "pots": 10, "prix": "3.95"} for index in range(1, 6)
    ]
    values = {"client": "A & B", "lignes_produits": rows}

    preview = templates_client.post(
        f"{TEMPLATES}/{template_id}/preview",
        headers=admin_headers,
        json={"values": values},
    )
    assert preview.status_code == 200
    assert "Total: 50 / €197,50" in preview.text
    assert r"A \& B" in preview.text

    generated = templates_client.post(
        f"{TEMPLATES}/{template_id}/generate",
        headers=operator_headers,
        json={"values": values},
    )
    assert generated.status_code == 201, generated.text
    document = generated.json()
    assert len(document["values"]["lignes_produits"]) == 5
    assert document["values"]["lignes_produits"][0] == {
        "designation": "Produit 1",
        "pots": 10,
        "prix": "3.95",
    }


def test_static_image_is_embedded_in_the_pdf(
    templates_client: TestClient,
    admin_headers: dict[str, str],
    operator_headers: dict[str, str],
    template_settings: Settings,
) -> None:
    source = r"""\documentclass{article}
\usepackage{graphicx}
\begin{document}
\includegraphics[width=1cm]{<< logo >>}
\end{document}
"""
    template = _upload_template(
        templates_client,
        admin_headers,
        name="Image",
        source=source,
    )
    template_id = template["id"]
    variable = templates_client.post(
        f"{TEMPLATES}/{template_id}/variables",
        headers=admin_headers,
        json={
            "name": "logo",
            "label": "Logo",
            "kind": "static",
            "value_type": "image",
            "value": None,
        },
    )
    assert variable.status_code == 201
    variable_id = variable.json()["id"]
    uploaded = templates_client.put(
        f"{TEMPLATES}/{template_id}/variables/{variable_id}/image",
        headers=admin_headers,
        files={"file": ("logo.png", PNG, "image/png")},
    )
    assert uploaded.status_code == 200

    generated = templates_client.post(
        f"{TEMPLATES}/{template_id}/generate",
        headers=operator_headers,
        json={"values": {}},
    )
    assert generated.status_code == 201, generated.text
    document = generated.json()
    assert document["values"]["logo"]["filename"] == "logo.png"

    pdf_path = next(template_settings.template_document_storage_dir.iterdir())
    assert pdf_path.read_bytes().startswith(b"%PDF")
    if shutil.which("pdfimages"):
        listing = subprocess.run(
            ["pdfimages", "-list", str(pdf_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert listing.returncode == 0
        assert "image" in listing.stdout


def test_missing_image_asset_is_reported_before_compilation(
    templates_client: TestClient,
    admin_headers: dict[str, str],
    operator_headers: dict[str, str],
) -> None:
    source = r"""\documentclass{article}
\usepackage{graphicx}
\begin{document}
\includegraphics{<< logo >>}
\end{document}
"""
    template = _upload_template(
        templates_client,
        admin_headers,
        name="Image absente",
        source=source,
    )
    template_id = template["id"]
    templates_client.post(
        f"{TEMPLATES}/{template_id}/variables",
        headers=admin_headers,
        json={
            "name": "logo",
            "label": "Logo",
            "kind": "static",
            "value_type": "image",
            "value": None,
        },
    )

    response = templates_client.post(
        f"{TEMPLATES}/{template_id}/generate",
        headers=operator_headers,
        json={"values": {}},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "template_image_missing"
    assert templates_client.get(DOCUMENTS, headers=operator_headers).json() == []
