from __future__ import annotations

import pytest


pytestmark = pytest.mark.api


def test_health_endpoint_is_live(api_client: object) -> None:
    """The health endpoint must report a live application, not a static stub."""

    response = api_client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert payload.get("status") in {"ok", "healthy"}
