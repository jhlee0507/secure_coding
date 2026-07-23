import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import User


@pytest.fixture()
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key-that-is-long-and-random-enough",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.sqlite3'}",
            "WTF_CSRF_ENABLED": False,
            "RATELIMIT_ENABLED": False,
            "INITIAL_DEMO_BALANCE": 100_000,
        }
    )
    with application.app_context():
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_user(app):
    def factory(username, password="Valid!Pass1", **kwargs):
        with app.app_context():
            user = User(
                username=username,
                password_hash=generate_password_hash(password, method="scrypt"),
                balance=kwargs.pop("balance", 100_000),
                **kwargs,
            )
            db.session.add(user)
            db.session.commit()
            return user.id

    return factory


@pytest.fixture()
def login(client):
    def perform(username, password="Valid!Pass1"):
        return client.post(
            "/auth/login", data={"username": username, "password": password}
        )

    return perform

