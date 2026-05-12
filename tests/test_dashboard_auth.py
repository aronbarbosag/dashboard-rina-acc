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
