from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db.session import get_session_factory
from app.schemas.health import LivenessResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=LivenessResponse)
async def liveness() -> LivenessResponse:
    return LivenessResponse(status="ok")


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse, "description": "A dependency is unavailable"}},
)
async def readiness(request: Request) -> JSONResponse:
    database_ok = await _check_database()
    mqtt_ok = bool(getattr(request.app.state, "mqtt", None) and request.app.state.mqtt.connected)

    checks = {
        "database": "ok" if database_ok else "error",
        "mqtt": "ok" if mqtt_ok else "down",
    }
    ready = database_ok and mqtt_ok
    return JSONResponse(
        status_code=200 if ready else 503,
        content=ReadinessResponse(
            status="ok" if ready else "degraded",
            checks=checks,
        ).model_dump(),
    )


async def _check_database() -> bool:
    try:
        async with get_session_factory()() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        return False
    return True
