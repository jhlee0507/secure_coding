from app.extensions import db
from app.models import AuditLog, User


def test_register_hashes_password(client, app):
    response = client.post(
        "/auth/register",
        data={"username": "new_user", "password": "Strong!Pass1"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.username == "new_user"))
        assert user is not None
        assert user.password_hash != "Strong!Pass1"
        assert "scrypt" in user.password_hash


def test_weak_password_is_rejected(client, app):
    response = client.post(
        "/auth/register", data={"username": "new_user", "password": "password"}
    )
    assert response.status_code == 200
    with app.app_context():
        assert db.session.scalar(db.select(User).where(User.username == "new_user")) is None


def test_login_rotates_existing_session(client, make_user):
    make_user("alice")
    with client.session_transaction() as session:
        session["attacker_value"] = "must disappear"
    response = client.post(
        "/auth/login", data={"username": "alice", "password": "Valid!Pass1"}
    )
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert "attacker_value" not in session
        assert session["user_id"]


def test_banned_user_session_is_revoked(client, app, make_user, login):
    user_id = make_user("alice")
    login("alice")
    with app.app_context():
        user = db.session.get(User, user_id)
        user.is_banned = True
        db.session.commit()
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_security_headers_are_present(client):
    response = client.get("/")
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "object-src 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Cache-Control"] == "no-store"


def test_post_without_csrf_is_rejected(tmp_path):
    from app import create_app

    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "csrf-test-secret-key-that-is-long-enough",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'csrf.sqlite3'}",
            "WTF_CSRF_ENABLED": True,
            "RATELIMIT_ENABLED": False,
        }
    )
    response = application.test_client().post(
        "/auth/register", data={"username": "alice", "password": "Strong!Pass1"}
    )
    assert response.status_code == 400


def test_production_cookie_mode_rejects_default_secret():
    import pytest
    from app import create_app

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app({"TESTING": True, "SESSION_COOKIE_SECURE": True})


def test_external_next_url_is_not_used(client, make_user):
    make_user("alice")
    response = client.post(
        "/auth/login?next=https://evil.example/steal",
        data={"username": "alice", "password": "Valid!Pass1"},
    )
    assert response.status_code == 302
    assert response.location.endswith("/dashboard")


def test_password_change_reauthenticates_and_revokes_session(
    client, app, make_user, login
):
    user_id = make_user("alice")
    login("alice")
    response = client.post(
        "/auth/profile",
        data={
            "action": "change_password",
            "current_password": "Valid!Pass1",
            "new_password": "New!ValidPass2",
            "password_confirmation": "New!ValidPass2",
        },
    )
    assert response.status_code == 302
    assert response.location.endswith("/auth/login")
    with client.session_transaction() as session:
        assert "user_id" not in session
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.password_hash != "New!ValidPass2"
        assert db.session.scalar(
            db.select(AuditLog).where(AuditLog.action == "password_change")
        )
    assert login("alice", "Valid!Pass1").status_code == 200
    assert login("alice", "New!ValidPass2").status_code == 302


def test_password_change_rejects_wrong_current_password(
    client, app, make_user, login
):
    user_id = make_user("alice")
    login("alice")
    response = client.post(
        "/auth/profile",
        data={
            "action": "change_password",
            "current_password": "Wrong!Pass1",
            "new_password": "New!ValidPass2",
            "password_confirmation": "New!ValidPass2",
        },
    )
    assert response.status_code == 200
    assert "현재 비밀번호가 올바르지 않습니다" in response.get_data(as_text=True)
    with client.session_transaction() as session:
        assert session["user_id"] == user_id


def test_production_mode_requires_secure_cookie_and_strong_secret():
    import pytest
    from app import create_app

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(
            {
                "TESTING": True,
                "APP_ENV": "production",
                "SESSION_COOKIE_SECURE": True,
            }
        )
    with pytest.raises(RuntimeError, match="COOKIE_SECURE"):
        create_app(
            {
                "TESTING": True,
                "APP_ENV": "production",
                "SECRET_KEY": "a-strong-production-secret-key-value",
                "SESSION_COOKIE_SECURE": False,
            }
        )
