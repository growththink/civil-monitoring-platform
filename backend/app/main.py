"""FastAPI application entrypoint.

On startup:
  - Configure logging
  - Start MQTT subscriber as background task
  - Start APScheduler with hourly Modbus poll + hourly export jobs

On shutdown:
  - Cancel MQTT task
  - Stop scheduler
  - Dispose DB engine
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router, ws_router
from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import AppException
from app.core.logging import configure_logging, get_logger
from app.workers.mqtt_subscriber import run_mqtt_subscriber
from app.workers.scheduler import configure_scheduler, scheduler

configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup.begin", env=settings.APP_ENV)

    # Background MQTT subscriber
    mqtt_task: asyncio.Task | None = None
    try:
        mqtt_task = asyncio.create_task(run_mqtt_subscriber(), name="mqtt-subscriber")
        log.info("startup.mqtt_started")
    except Exception as e:
        log.error("startup.mqtt_failed", error=str(e))

    # Scheduler
    try:
        await configure_scheduler()
        scheduler.start()
        log.info("startup.scheduler_started")
    except Exception as e:
        log.error("startup.scheduler_failed", error=str(e))

    log.info("startup.complete")
    yield
    log.info("shutdown.begin")

    # Stop scheduler
    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
    except Exception as e:
        log.warning("shutdown.scheduler_error", error=str(e))

    # Cancel MQTT
    if mqtt_task and not mqtt_task.done():
        mqtt_task.cancel()
        try:
            await mqtt_task
        except (asyncio.CancelledError, Exception):
            pass

    await engine.dispose()
    log.info("shutdown.complete")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Civil engineering / geotechnical monitoring platform",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=400,
        content={"code": exc.code, "message": exc.message},
    )


@app.get("/health", tags=["health"])
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
    }


# REST API
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# WebSocket
app.include_router(ws_router)
