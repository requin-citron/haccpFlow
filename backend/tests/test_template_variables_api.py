from __future__ import annotations

from fastapi.testclient import TestClient

TEMPLATES = "/api/v1/templates"
SOURCE = (
    b"\\documentclass{article}\n\\begin{document}\n<< client >> << company >>\n\\end{document}\n"
)


def _upload_template(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str = "Modele",
    source: bytes = SOURCE,
) -> dict:
    response = client.post(
        TEMPLATES,
        headers=headers,
        data={"name": name},
        files={"file": (f"{name}.tex", source, "text/plain")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _variable(
    name: str,
    *,
    kind: str = "local",
    value_type: str = "text",
    value: str | list[dict] | None = None,
    label: str | None = None,
) -> dict:
    return {
        "name": name,
        "label": label or name,
        "kind": kind,
        "value_type": value_type,
        "value": value,
    }


def test_admin_can_manage_variables_and_usage_is_computed(
    templates_client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    template = _upload_template(templates_client, admin_headers)
    variables_path = f"{TEMPLATES}/{template['id']}/variables"

    client_variable = templates_client.post(
        variables_path,
        headers=admin_headers,
        json=_variable("client", label="Nom du client"),
    )
    assert client_variable.status_code == 201
    assert client_variable.json()["used_in_template"] is True

    company = templates_client.post(
        variables_path,
        headers=admin_headers,
        json=_variable("company", kind="static", value="La LEGU"),
    )
    assert company.status_code == 201
    assert company.json()["value"] == "La LEGU"

    unused = templates_client.post(
        variables_path,
        headers=admin_headers,
        json=_variable("unused"),
    )
    assert unused.status_code == 201

    listing = templates_client.get(variables_path, headers=admin_headers)
    assert listing.status_code == 200
    by_name = {item["name"]: item for item in listing.json()}
    assert by_name["client"]["used_in_template"] is True
    assert by_name["company"]["used_in_template"] is True
    assert by_name["unused"]["used_in_template"] is False

    updated = templates_client.put(
        f"{variables_path}/{client_variable.json()['id']}",
        headers=admin_headers,
        json=_variable("client_nom", label="Nom du client"),
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "client_nom"
    assert updated.json()["used_in_template"] is False

    deleted = templates_client.delete(
        f"{variables_path}/{unused.json()['id']}",
        headers=admin_headers,
    )
    assert deleted.status_code == 204
    assert [
        item["name"] for item in templates_client.get(variables_path, headers=admin_headers).json()
    ] == ["client_nom", "company"]


def test_operator_can_read_but_not_edit_variables(
    templates_client: TestClient,
    admin_headers: dict[str, str],
    operator_headers: dict[str, str],
) -> None:
    template = _upload_template(templates_client, admin_headers)
    variables_path = f"{TEMPLATES}/{template['id']}/variables"
    created = templates_client.post(
        variables_path,
        headers=admin_headers,
        json=_variable("client"),
    ).json()

    assert templates_client.get(TEMPLATES, headers=operator_headers).status_code == 200
    assert (
        templates_client.get(
            f"{TEMPLATES}/{template['id']}/download", headers=operator_headers
        ).status_code
        == 403
    )
    assert templates_client.get(variables_path, headers=operator_headers).status_code == 200
    assert (
        templates_client.post(
            variables_path,
            headers=operator_headers,
            json=_variable("other"),
        ).status_code
        == 403
    )
    assert (
        templates_client.put(
            f"{variables_path}/{created['id']}",
            headers=operator_headers,
            json=_variable("client"),
        ).status_code
        == 403
    )
    assert (
        templates_client.delete(
            f"{variables_path}/{created['id']}",
            headers=operator_headers,
        ).status_code
        == 403
    )
    assert templates_client.get(variables_path).status_code == 401


def test_duplicate_names_are_scoped_to_the_template(
    templates_client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    first = _upload_template(templates_client, admin_headers, name="Premier")
    second = _upload_template(templates_client, admin_headers, name="Second")

    assert (
        templates_client.post(
            f"{TEMPLATES}/{first['id']}/variables",
            headers=admin_headers,
            json=_variable("client"),
        ).status_code
        == 201
    )
    duplicate = templates_client.post(
        f"{TEMPLATES}/{first['id']}/variables",
        headers=admin_headers,
        json=_variable("client"),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "template_variable_name_taken"

    assert (
        templates_client.post(
            f"{TEMPLATES}/{second['id']}/variables",
            headers=admin_headers,
            json=_variable("client"),
        ).status_code
        == 201
    )


def test_invalid_variable_payloads_are_rejected(
    templates_client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    template = _upload_template(templates_client, admin_headers)
    variables_path = f"{TEMPLATES}/{template['id']}/variables"

    invalid_name = templates_client.post(
        variables_path,
        headers=admin_headers,
        json=_variable("2client"),
    )
    assert invalid_name.status_code == 422
    assert invalid_name.json()["code"] == "template_variable_invalid"

    static_without_value = templates_client.post(
        variables_path,
        headers=admin_headers,
        json=_variable("company", kind="static"),
    )
    assert static_without_value.status_code == 422
    assert static_without_value.json()["code"] == "template_value_invalid"

    invalid_date = templates_client.post(
        variables_path,
        headers=admin_headers,
        json=_variable("date", value_type="date", value="22/08/2026"),
    )
    assert invalid_date.status_code == 422
    assert invalid_date.json()["code"] == "template_value_invalid"

    assert (
        templates_client.post(
            variables_path,
            headers=admin_headers,
            json=_variable("amount", value_type="number", value="3,95"),
        ).json()["value"]
        == "3.95"
    )


def test_products_variable_round_trip(
    templates_client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    template = _upload_template(templates_client, admin_headers)
    variables_path = f"{TEMPLATES}/{template['id']}/variables"
    payload = _variable(
        "lignes_produits",
        value_type="products",
        value=[{"designation": "Bocal", "pots": 10, "prix": "3,95"}],
    )

    created = templates_client.post(
        variables_path,
        headers=admin_headers,
        json=payload,
    )

    assert created.status_code == 201
    assert created.json()["value"] == [
        {"designation": "Bocal", "pots": 10, "prix": "3.95"}
    ]
    listing = templates_client.get(variables_path, headers=admin_headers)
    assert listing.json()[0]["value"] == [
        {"designation": "Bocal", "pots": 10, "prix": "3.95"}
    ]

    invalid = templates_client.post(
        variables_path,
        headers=admin_headers,
        json=_variable(
            "lignes_invalides",
            value_type="products",
            value=[{"designation": "  ", "pots": 1, "prix": "1"}],
        ),
    )
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "template_value_invalid"
