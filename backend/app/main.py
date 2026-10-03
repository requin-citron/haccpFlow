from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.db.session import dispose_engine
from app.mqtt.client import MqttClient
from app.seed import seed_admin_user

logger = logging.getLogger(__name__)

DESCRIPTION = """
API de gestion HACCP : plans de maîtrise, équipements, mesures et seuils
configurables. Toutes les dates sont en UTC.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = get_settings()

    mqtt_client = MqttClient(settings)
    mqtt_client.start()
    app.state.mqtt = mqtt_client

    await seed_admin_user(settings)

    try:
        yield
    finally:
        mqtt_client.stop()
        await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    docs_url = "/docs" if settings.docs_enabled else None
    redoc_url = "/redoc" if settings.docs_enabled else None
    openapi_url = "/openapi.json" if settings.docs_enabled else None

    app = FastAPI(
        title="haccpFlow API",
        version="0.1.0",
        description=DESCRIPTION,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        servers=[{"url": settings.public_api_url}] if settings.public_api_url else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_router)

    return app


app = create_app()
