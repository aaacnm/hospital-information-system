"""Shared fixtures for contract and API tests.

The repository starts before the application packages are created. API tests
therefore skip explicitly until ``backend/app/main.py`` is available; they do
not substitute a fake application or fake response.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if BACKEND.is_dir():
    # The planned package layout is backend/app; expose backend as an import root
    # without requiring the application to be installed during local test runs.
    sys.path.insert(0, str(BACKEND))


@pytest.fixture
def api_client() -> Iterator[object]:
    """Return a real FastAPI TestClient once the backend application exists."""

    try:
        fastapi_testclient = importlib.import_module("fastapi.testclient")
    except ModuleNotFoundError as exc:
        pytest.skip(f"FastAPI test dependency is not installed: {exc.name}")

    try:
        main_module = importlib.import_module("app.main")
    except ModuleNotFoundError as exc:
        if exc.name == "app" or exc.name.startswith("app."):
            pytest.skip("backend/app/main.py is not implemented yet")
        pytest.skip(f"backend dependency is not installed: {exc.name}")

    application = getattr(main_module, "app", None)
    if application is None:
        pytest.fail("backend app.main must expose a FastAPI application named 'app'")

    yield fastapi_testclient.TestClient(application)
