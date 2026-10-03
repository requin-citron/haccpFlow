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
    f"{API_V1_PREFIX}/equipment",
    f"{API_V1_PREFIX}/equipment/{{equipment_id}}",
    f"{API_V1_PREFIX}/equipment/{{equipment_id}}/readings",
    f"{API_V1_PREFIX}/equipment/{{equipment_id}}/readings/{{reading_date}}",
    f"{API_V1_PREFIX}/equipment/{{equipment_id}}/readings/{{reading_date}}/history",
    f"{API_V1_PREFIX}/users",
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
