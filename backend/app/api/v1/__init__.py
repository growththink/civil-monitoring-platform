"""Combine all v1 routers."""
from fastapi import APIRouter

from app.api.v1 import alerts, auth, devices, ingest, readings, sensors, settings as settings_api, sites, ws

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(sites.router)
api_router.include_router(devices.router)
api_router.include_router(sensors.router)
api_router.include_router(readings.router)
api_router.include_router(ingest.router)
api_router.include_router(alerts.router)
api_router.include_router(settings_api.router)

# WebSocket router (no prefix)
ws_router = ws.router
