from contextlib import asynccontextmanager

import pytest

from app.main import app


@pytest.fixture(autouse=True)
def disable_database_startup_for_unit_tests(monkeypatch):
    """Skip database initialization for tests that don't require PostgreSQL."""

    @asynccontextmanager
    async def test_lifespan(application):
        yield

    monkeypatch.setattr(
        app.router,
        "lifespan_context",
        test_lifespan,
    )
