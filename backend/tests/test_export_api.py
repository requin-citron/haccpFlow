from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

EXPORTS = "/api/v1/exports"
EQUIPMENT = "/api/v1/equipment"
PLANS = "/api/v1/cleaning-plans"
BATCHES = "/api/v1/pasteurisations"
TRANSPORTS = "/api/v1/transports"
VEHICLES = "/api/v1/vehicles"

DATASETS = ["readings", "cleanings", "pasteurisations", "transports"]

TRICKY_COMMENT = 'Produit A ; rinçage "complet"\nseconde ligne'


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def _days_ago(days: int) -> str:
    return (datetime.now(UTC).date() - timedelta(days=days)).isoformat()


def _rows(response: Any) -> list[list[str]]:
    """A CSV exported for Excel: BOM, semicolons, and quoted values."""

    assert response.content.startswith(b"\xef\xbb\xbf"), "UTF-8 BOM missing"
    text = response.content.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text), delimiter=";"))


def _seed(api_client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    """Create one exportable row of each kind."""

    equipment = api_client.post(
        EQUIPMENT, json={"name": "Frigo export", "type": "fridge"}, headers=headers
    ).json()
    api_client.put(
        f"{EQUIPMENT}/{equipment['id']}/readings/{_today()}",
        json={"morning_celsius": 2.5, "evening_celsius": 9},
        headers=headers,
    )

    plan = api_client.post(
        PLANS,
        json={"name": "Zone export", "frequency": "daily", "products": "Détergent"},
        headers=headers,
    ).json()
    api_client.post(
        f"{PLANS}/{plan['id']}/records",
        json={"cleaning_date": _today(), "comment": TRICKY_COMMENT},
        headers=headers,
    )

    vehicle = api_client.post(
        VEHICLES,
        json={"name": "Camion export", "plate": "EX-123-PO"},
        headers=headers,
    ).json()
    batch = api_client.post(
        BATCHES,
        json={
            "batch_date": _today(),
            "product_name": "Crème export",
            "lot_number": "LOT-EXPORT",
            "quantity": 42,
        },
        headers=headers,
    ).json()
    api_client.put(
        f"{BATCHES}/{batch['id']}/phases/preheating",
        json={
            "started_at": "09:00",
            "ended_at": "09:30",
            "target_temperature_celsius": 85,
            "observation": "RAS",
        },
        headers=headers,
    )
    transport = api_client.post(
        TRANSPORTS,
        json={
            "transport_date": _today(),
            "place": "Boulangerie export",
            "product_name": "Crème export",
            "lot_number": "LOT-EXPORT",
            "vehicle_id": vehicle["id"],
            "departure_time": "08:00",
            "departure_temperature_celsius": 3.5,
        },
        headers=headers,
    ).json()

    return {
        "equipment": equipment,
        "plan": plan,
        "batch": batch,
        "transport": transport,
    }


@pytest.mark.parametrize("dataset", DATASETS)
def test_every_dataset_is_served_as_a_csv(
    api_client: TestClient, admin_headers: dict[str, str], dataset: str
) -> None:
    response = api_client.get(f"{EXPORTS}/{dataset}", headers=admin_headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    disposition = response.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="')
    assert disposition.endswith(f'-complet-{_today()}.csv"')


def test_the_readings_export_lists_the_values(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    _seed(api_client, admin_headers)

    rows = _rows(api_client.get(f"{EXPORTS}/readings", headers=admin_headers))

    assert rows[0][0] == "Matériel"
    assert rows[0][4] == "Température (°C)"
    morning = next(row for row in rows[1:] if row[3] == "Matin")
    assert morning[0] == "Frigo export"
    assert morning[1] == "Réfrigérateur"
    assert morning[4] == "2,50"
    assert morning[5] == "Oui"
    assert morning[6] == "Manuel"
    assert morning[2] == datetime.now(UTC).date().strftime("%d/%m/%Y")
    evening = next(row for row in rows[1:] if row[3] == "Soir")
    assert evening[5] == "Non"


def test_the_cleanings_export_escapes_free_text(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    _seed(api_client, admin_headers)

    rows = _rows(api_client.get(f"{EXPORTS}/cleanings", headers=admin_headers))

    record = next(row for row in rows[1:] if row[0] == "Zone export")
    assert record[1] == "Quotidien"
    assert record[3] == datetime.now(UTC).date().strftime("%d/%m/%Y")
    assert record[4] == TRICKY_COMMENT
    assert record[5] == "admin@test.local"


def test_the_pasteurisation_export_lays_out_the_phases(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    _seed(api_client, admin_headers)

    rows = _rows(api_client.get(f"{EXPORTS}/pasteurisations", headers=admin_headers))

    headers = rows[0]
    assert headers[:4] == ["Date", "Produit", "N° de lot", "Quantité"]
    assert "Préchauffage — durée (min)" in headers
    assert "Refroidissement — observation" in headers
    assert headers[-1] == "Phases"

    batch = next(row for row in rows[1:] if row[2] == "LOT-EXPORT")
    duration_index = headers.index("Préchauffage — durée (min)")
    assert batch[1] == "Crème export"
    assert batch[3] == "42"
    assert batch[duration_index] == "30"
    assert batch[-1] == "Incomplet"


def test_the_transport_export_shows_the_vehicle(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    _seed(api_client, admin_headers)
    api_client.post(
        TRANSPORTS,
        json={
            "transport_date": _today(),
            "place": "Épicerie export",
            "product_name": "Glace export",
            "vehicle_label": "Transporteur externe 999",
        },
        headers=admin_headers,
    )

    rows = _rows(api_client.get(f"{EXPORTS}/transports", headers=admin_headers))
    headers = rows[0]

    referenced = next(row for row in rows[1:] if row[1] == "Crème export")
    assert referenced[headers.index("Véhicule")] == "Camion export"
    assert referenced[headers.index("Plaque")] == "EX-123-PO"
    assert referenced[headers.index("Véhicule référencé")] == "Oui"
    assert referenced[headers.index("Départ — température (°C)")] == "3,50"
    assert referenced[headers.index("Chaîne du froid")] == "En cours"

    external = next(row for row in rows[1:] if row[1] == "Glace export")
    assert external[headers.index("Véhicule")] == "Transporteur externe 999"
    assert external[headers.index("Véhicule référencé")] == "Non"
    assert external[headers.index("Plaque")] == ""


def test_a_deactivated_row_is_still_exported(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    seeded = _seed(api_client, admin_headers)
    api_client.delete(f"{EQUIPMENT}/{seeded['equipment']['id']}", headers=admin_headers)
    api_client.delete(f"{PLANS}/{seeded['plan']['id']}", headers=admin_headers)

    readings = _rows(api_client.get(f"{EXPORTS}/readings", headers=admin_headers))
    cleanings = _rows(api_client.get(f"{EXPORTS}/cleanings", headers=admin_headers))

    # The status column is gone, but a deactivated row must stay: an archive
    # that silently drops it would be incomplete.
    assert any(row[0] == "Frigo export" for row in readings[1:])
    assert any(row[0] == "Zone export" for row in cleanings[1:])


def test_a_deactivated_transport_is_still_exported(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    seeded = _seed(api_client, admin_headers)
    api_client.delete(f"{TRANSPORTS}/{seeded['transport']['id']}", headers=admin_headers)

    rows = _rows(api_client.get(f"{EXPORTS}/transports", headers=admin_headers))
    transport = next(row for row in rows[1:] if row[1] == "Crème export")

    assert transport[1] == "Crème export"


def test_the_date_range_filters_the_rows(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    seeded = _seed(api_client, admin_headers)
    api_client.put(
        f"{EQUIPMENT}/{seeded['equipment']['id']}/readings/{_days_ago(10)}",
        json={"morning_celsius": 1},
        headers=admin_headers,
    )

    filtered = api_client.get(
        f"{EXPORTS}/readings?from={_days_ago(1)}&to={_today()}", headers=admin_headers
    )
    rows = _rows(filtered)

    assert filtered.status_code == 200
    assert filtered.headers["content-disposition"].endswith(f'{_days_ago(1)}-{_today()}.csv"')
    assert len(rows) == 3  # header + matin + soir
    assert all(len(row) == len(rows[0]) for row in rows)


def test_an_inverted_range_is_rejected(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = api_client.get(
        f"{EXPORTS}/readings?from={_today()}&to={_days_ago(1)}", headers=admin_headers
    )

    assert response.status_code == 422
    assert response.json()["code"] == "export_range_invalid"


def test_an_unknown_dataset_is_rejected(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = api_client.get(f"{EXPORTS}/factures", headers=admin_headers)

    assert response.status_code == 422


def test_an_operator_can_export(api_client: TestClient, operator_headers: dict[str, str]) -> None:
    response = api_client.get(f"{EXPORTS}/transports", headers=operator_headers)

    assert response.status_code == 200


def test_exports_require_authentication(api_client: TestClient) -> None:
    assert api_client.get(f"{EXPORTS}/readings").status_code == 401
