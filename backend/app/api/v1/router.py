from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, cleaning_plans, cleaning_schedule, equipment, readings, users
from app.config import API_V1_PREFIX

api_router = APIRouter(prefix=API_V1_PREFIX)
api_router.include_router(auth.router)
api_router.include_router(cleaning_plans.router)
api_router.include_router(cleaning_schedule.router)
api_router.include_router(equipment.router)
api_router.include_router(readings.router)
api_router.include_router(users.router)
