from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    cash_registers,
    cash_sessions,
    cleaning_plans,
    cleaning_schedule,
    equipment,
    exports,
    history,
    pasteurisations,
    readings,
    transports,
    users,
    vehicles,
)
from app.config import API_V1_PREFIX

api_router = APIRouter(prefix=API_V1_PREFIX)
api_router.include_router(auth.router)
api_router.include_router(cash_registers.router)
api_router.include_router(cash_sessions.router)
api_router.include_router(cleaning_plans.router)
api_router.include_router(cleaning_schedule.router)
api_router.include_router(equipment.router)
api_router.include_router(exports.router)
api_router.include_router(history.router)
api_router.include_router(pasteurisations.router)
api_router.include_router(readings.router)
api_router.include_router(transports.router)
api_router.include_router(users.router)
api_router.include_router(vehicles.router)
