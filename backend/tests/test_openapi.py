from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import API_V1_PREFIX, get_settings
from app.main import create_app

EXPECTED_PATHS = {
    "/health/live",
    "/health/ready",
    f"{API_V1_PREFIX}/auth/login",
    f"{API_V1_PREFIX}/auth/refresh",
    f"{API_V1_PREFIX}/auth/logout",
    f"{API_V1_PREFIX}/auth/me",
    f"{API_V1_PREFIX}/cash-registers",
    f"{API_V1_PREFIX}/cash-registers/{{cash_register_id}}",
    f"{API_V1_PREFIX}/cash-sessions",
    f"{API_V1_PREFIX}/cash-sessions/{{session_id}}",
    f"{API_V1_PREFIX}/cash-sessions/{{session_id}}/close",
    f"{API_V1_PREFIX}/cash-sessions/{{session_id}}/expenses",
    f"{API_V1_PREFIX}/cash-sessions/{{session_id}}/expenses/{{expense_id}}",
    f"{API_V1_PREFIX}/cleaning-plans",
    f"{API_V1_PREFIX}/cleaning-plans/{{plan_id}}",
    f"{API_V1_PREFIX}/cleaning-plans/{{plan_id}}/records",
    f"{API_V1_PREFIX}/cleaning-plans/{{plan_id}}/records/{{record_id}}",
    f"{API_V1_PREFIX}/cleaning-plans/{{plan_id}}/records/{{record_id}}/history",
    f"{API_V1_PREFIX}/cleaning-schedule",
    f"{API_V1_PREFIX}/cleaning-schedule/overdue",
    f"{API_V1_PREFIX}/equipment",
    f"{API_V1_PREFIX}/equipment/{{equipment_id}}",
    f"{API_V1_PREFIX}/equipment/{{equipment_id}}/readings",
    f"{API_V1_PREFIX}/equipment/{{equipment_id}}/readings/{{reading_date}}",
    f"{API_V1_PREFIX}/equipment/{{equipment_id}}/readings/{{reading_date}}/history",
    f"{API_V1_PREFIX}/exports/{{dataset}}",
    f"{API_V1_PREFIX}/history",
    f"{API_V1_PREFIX}/pasteurisations",
    f"{API_V1_PREFIX}/pasteurisations/{{batch_id}}",
    f"{API_V1_PREFIX}/pasteurisations/{{batch_id}}/phases/{{phase}}",
    f"{API_V1_PREFIX}/pasteurisations/{{batch_id}}/phases/{{phase}}/history",
    f"{API_V1_PREFIX}/transports",
    f"{API_V1_PREFIX}/transports/{{transport_id}}",
    f"{API_V1_PREFIX}/transports/{{transport_id}}/readings",
    f"{API_V1_PREFIX}/users",
    f"{API_V1_PREFIX}/vehicles",
    f"{API_V1_PREFIX}/vehicles/{{vehicle_id}}",
}


def test_openapi_exposes_the_expected_surface() -> None:
    schema = create_app().openapi()

    assert set(schema["paths"]) == EXPECTED_PATHS


def test_openapi_keeps_the_oauth2_password_flow() -> None:
    schema = create_app().openapi()
    scheme = schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]

    assert scheme["type"] == "oauth2"
    assert scheme["flows"]["password"]["tokenUrl"] == f"{API_V1_PREFIX}/auth/login"


def test_equipment_routes_expose_the_expected_methods() -> None:
    schema = create_app().openapi()

    collection = schema["paths"][f"{API_V1_PREFIX}/equipment"]
    item = schema["paths"][f"{API_V1_PREFIX}/equipment/{{equipment_id}}"]

    assert set(collection) == {"get", "post"}
    assert set(item) == {"delete", "put"}


def test_reading_routes_expose_the_expected_methods() -> None:
    schema = create_app().openapi()

    collection = schema["paths"][f"{API_V1_PREFIX}/equipment/{{equipment_id}}/readings"]
    day = schema["paths"][f"{API_V1_PREFIX}/equipment/{{equipment_id}}/readings/{{reading_date}}"]
    history = schema["paths"][
        f"{API_V1_PREFIX}/equipment/{{equipment_id}}/readings/{{reading_date}}/history"
    ]

    assert set(collection) == {"get"}
    assert set(day) == {"get", "put"}
    assert set(history) == {"get"}


def test_cleaning_routes_expose_the_expected_methods() -> None:
    schema = create_app().openapi()
    prefix = API_V1_PREFIX

    assert set(schema["paths"][f"{prefix}/cleaning-plans"]) == {"get", "post"}
    assert set(schema["paths"][f"{prefix}/cleaning-plans/{{plan_id}}"]) == {"delete", "put"}
    assert set(schema["paths"][f"{prefix}/cleaning-plans/{{plan_id}}/records"]) == {
        "get",
        "post",
    }
    assert set(schema["paths"][f"{prefix}/cleaning-plans/{{plan_id}}/records/{{record_id}}"]) == {
        "delete",
        "put",
    }
    assert set(
        schema["paths"][f"{prefix}/cleaning-plans/{{plan_id}}/records/{{record_id}}/history"]
    ) == {"get"}
    assert set(schema["paths"][f"{prefix}/cleaning-schedule"]) == {"get"}
    assert set(schema["paths"][f"{prefix}/cleaning-schedule/overdue"]) == {"get"}


def test_pasteurisation_routes_expose_the_expected_methods() -> None:
    schema = create_app().openapi()
    prefix = API_V1_PREFIX

    assert set(schema["paths"][f"{prefix}/pasteurisations"]) == {"get", "post"}
    assert set(schema["paths"][f"{prefix}/pasteurisations/{{batch_id}}"]) == {
        "delete",
        "get",
        "put",
    }
    assert set(schema["paths"][f"{prefix}/pasteurisations/{{batch_id}}/phases/{{phase}}"]) == {
        "put"
    }
    assert set(
        schema["paths"][f"{prefix}/pasteurisations/{{batch_id}}/phases/{{phase}}/history"]
    ) == {"get"}


def test_the_unified_history_is_read_only() -> None:
    schema = create_app().openapi()

    assert set(schema["paths"][f"{API_V1_PREFIX}/history"]) == {"get"}


def test_the_export_route_is_read_only() -> None:
    schema = create_app().openapi()

    assert set(schema["paths"][f"{API_V1_PREFIX}/exports/{{dataset}}"]) == {"get"}


def test_cash_register_routes_expose_the_expected_methods() -> None:
    schema = create_app().openapi()
    prefix = API_V1_PREFIX

    assert set(schema["paths"][f"{prefix}/cash-registers"]) == {"get", "post"}
    assert set(schema["paths"][f"{prefix}/cash-registers/{{cash_register_id}}"]) == {
        "delete",
        "put",
    }


def test_vehicle_and_transport_routes_expose_the_expected_methods() -> None:
    schema = create_app().openapi()
    prefix = API_V1_PREFIX

    assert set(schema["paths"][f"{prefix}/vehicles"]) == {"get", "post"}
    assert set(schema["paths"][f"{prefix}/vehicles/{{vehicle_id}}"]) == {"delete", "put"}
    assert set(schema["paths"][f"{prefix}/transports"]) == {"get", "post"}
    assert set(schema["paths"][f"{prefix}/transports/{{transport_id}}"]) == {
        "delete",
        "get",
        "put",
    }
    assert set(schema["paths"][f"{prefix}/transports/{{transport_id}}/readings"]) == {"put"}


def test_swagger_and_redoc_are_served() -> None:
    client = TestClient(create_app())

    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200


def test_documentation_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCS_ENABLED", "false")
    get_settings.cache_clear()
    try:
        app = create_app()

        assert app.docs_url is None
        assert app.redoc_url is None
        assert app.openapi_url is None
    finally:
        get_settings.cache_clear()
