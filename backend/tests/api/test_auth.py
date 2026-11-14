from tests.conftest import TEST_PASSWORD


def test_login_sets_cookie_and_returns_token(app_client) -> None:
    response = app_client.post("/auth/login", json={"password": TEST_PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["token"]
    assert body["expires_at"]
    cookie = response.headers["set-cookie"]
    assert "fitzy_session=" in cookie
    assert "HttpOnly" in cookie
    assert "samesite=lax" in cookie.lower()


def test_wrong_password_is_rejected(app_client) -> None:
    response = app_client.post("/auth/login", json={"password": "not the password"})
    assert response.status_code == 401
    assert "set-cookie" not in response.headers


def test_me_requires_a_session(app_client) -> None:
    assert app_client.get("/auth/me").status_code == 401


def test_cookie_session_works(app_client) -> None:
    app_client.post("/auth/login", json={"password": TEST_PASSWORD})
    assert app_client.get("/auth/me").status_code == 200  # TestClient keeps cookies


def test_bearer_token_works(app_client) -> None:
    token = app_client.post("/auth/login", json={"password": TEST_PASSWORD}).json()["token"]
    app_client.cookies.clear()
    response = app_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_logout_clears_cookie(app_client) -> None:
    app_client.post("/auth/login", json={"password": TEST_PASSWORD})
    response = app_client.post("/auth/logout")
    assert response.status_code == 204
    assert (
        'fitzy_session=""' in response.headers["set-cookie"]
        or "Max-Age=0" in response.headers["set-cookie"]
    )


def test_too_many_failures_are_throttled(app_client) -> None:
    for _ in range(5):
        assert app_client.post("/auth/login", json={"password": "wrong"}).status_code == 401
    response = app_client.post("/auth/login", json={"password": TEST_PASSWORD})
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0


def test_old_shared_secret_no_longer_works(app_client) -> None:
    from tests.conftest import TEST_AUTH_SECRET

    response = app_client.get("/auth/me", headers={"Authorization": f"Bearer {TEST_AUTH_SECRET}"})
    assert response.status_code == 401
