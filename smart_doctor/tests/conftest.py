import os

import pytest


def pytest_configure(config):
    os.environ["TESTING"] = "true"
    config.option.asyncio_mode = "auto"


@pytest.fixture(scope="session", autouse=True)
def _session_engine_cleanup():
    yield
    try:
        from app.infrastructure.persistence.database import engine
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(engine.dispose())
        loop.close()
    except Exception:
        pass