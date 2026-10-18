def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_and_me(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "cashier.demo", "password": "Demo123!"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "cashier.demo"
    assert me.json()["role"] == "cashier"


def test_invalid_login_returns_401(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "cashier.demo", "password": "wrong"},
    )
    assert response.status_code == 401


def test_me_without_token_returns_401(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_cashier_cannot_access_admin_probe(client):
    login = client.post(
        "/api/auth/login",
        data={"username": "cashier.demo", "password": "Demo123!"},
    )
    token = login.json()["access_token"]
    response = client.get("/api/admin/ping", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
