from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.core.errors import ApiError
from app.main import create_app


def _app_with_failure_routes() -> FastAPI:
    app = create_app()
    router = APIRouter()

    @router.get("/_test/api-error")
    async def api_error() -> None:
        raise ApiError(409, "conflict", "Already exists", context={"field": "email"})

    @router.get("/_test/crash")
    async def crash() -> None:
        raise RuntimeError("boom")

    app.include_router(router)
    return app


def _client() -> TestClient:
    return TestClient(_app_with_failure_routes(), raise_server_exceptions=False)


def test_api_error_uses_the_common_payload() -> None:
    response = _client().get("/_test/api-error")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Already exists",
        "code": "conflict",
        "context": {"field": "email"},
    }


def test_validation_error_uses_the_common_payload() -> None:
    response = _client().post("/api/v1/auth/refresh", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["detail"] == "Request validation failed"
    assert body["context"]["errors"]


def test_unknown_route_uses_the_common_payload() -> None:
    response = _client().get("/nope")

    assert response.status_code == 404
    assert response.json()["code"] == "http_404"


def test_unhandled_error_is_not_leaked() -> None:
    response = _client().get("/_test/crash")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Internal server error",
        "code": "internal_error",
        "context": None,
    }
