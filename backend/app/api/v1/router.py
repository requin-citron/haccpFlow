from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, equipment, users
from app.config import API_V1_PREFIX

api_router = APIRouter(prefix=API_V1_PREFIX)
api_router.include_router(auth.router)
api_router.include_router(equipment.router)
api_router.include_router(users.router)
