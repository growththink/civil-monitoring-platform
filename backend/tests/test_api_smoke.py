"""Smoke test — make sure the FastAPI app at least imports and registers routes."""
import os

os.environ.setdefault("SECRET_KEY", "x" * 64)


def test_app_imports():
    from app.main import app
    assert app.title == "Civil Monitoring Platform"


def test_routes_registered():
    from app.main import app
    paths = {route.path for route in app.routes}
    assert "/health" in paths
    # API v1 routes
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/sites" in paths
    assert "/api/v1/devices" in paths
    assert "/api/v1/sensors" in paths
    assert "/api/v1/alerts" in paths
    assert "/api/v1/ingest" in paths
    # WebSocket
    assert any(p.startswith("/ws") for p in paths)


def test_openapi_schema_generates():
    from app.main import app
    schema = app.openapi()
    assert schema["info"]["title"] == "Civil Monitoring Platform"
    assert "/api/v1/auth/login" in schema["paths"]


def test_health_endpoint_callable():
    """Health endpoint is a plain async function — call it directly."""
    import asyncio
    from app.main import health
    result = asyncio.run(health())
    assert result["status"] == "ok"
