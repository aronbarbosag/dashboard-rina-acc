import app.auth as auth


def test_check_dashboard_credentials_accepts_configured_login(monkeypatch):
    monkeypatch.setattr(auth, "DASHBOARD_USERNAME", "user")
    monkeypatch.setattr(auth, "DASHBOARD_PASSWORD", "secret")

    assert auth.check_dashboard_credentials("user", "secret") is True


def test_check_dashboard_credentials_rejects_invalid_login(monkeypatch):
    monkeypatch.setattr(auth, "DASHBOARD_USERNAME", "user")
    monkeypatch.setattr(auth, "DASHBOARD_PASSWORD", "secret")

    assert auth.check_dashboard_credentials("user", "wrong") is False
    assert auth.check_dashboard_credentials("wrong", "secret") is False


def test_auth_token_accepts_valid_cached_login(monkeypatch):
    monkeypatch.setattr(auth, "DASHBOARD_USERNAME", "user")
    monkeypatch.setattr(auth, "DASHBOARD_PASSWORD", "secret")
    monkeypatch.setattr(auth, "AUTH_CACHE_TTL_SECONDS", 60)

    token = auth.create_auth_token(username="user", issued_at=100)

    assert auth.validate_auth_token(token, now=120) is True


def test_auth_token_rejects_expired_or_tampered_login(monkeypatch):
    monkeypatch.setattr(auth, "DASHBOARD_USERNAME", "user")
    monkeypatch.setattr(auth, "DASHBOARD_PASSWORD", "secret")
    monkeypatch.setattr(auth, "AUTH_CACHE_TTL_SECONDS", 60)

    token = auth.create_auth_token(username="user", issued_at=100)
    payload, signature = token.rsplit(".", 1)

    assert auth.validate_auth_token(token, now=161) is False
    assert auth.validate_auth_token(f"{payload}x.{signature}", now=120) is False
