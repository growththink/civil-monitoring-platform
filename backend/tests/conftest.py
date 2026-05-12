"""Pytest configuration — sets a fake SECRET_KEY before any app import.

For full integration tests that hit the DB, run via docker compose against
a real Postgres + TimescaleDB instance.
"""
import os

os.environ.setdefault("SECRET_KEY", "x" * 64)
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
