from __future__ import annotations

import pytest


pytestmark = pytest.mark.api


def test_current_user_requires_authentication(api_client: object) -> None:
    """The current-user endpoint must reject requests without a token."""

    response = api_client.get("/api/auth/me")

    assert response.status_code == 401
