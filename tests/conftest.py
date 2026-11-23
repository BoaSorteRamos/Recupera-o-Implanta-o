import os

import pytest

from app import create_app
from app.models import db

# Integração roda contra PostgreSQL real quando TEST_DATABASE_URL está definida
# (mesmo banco da produção); sem ela, usa SQLite em memória.
TEST_DB = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": TEST_DB,
        "SECRET_KEY": "chave-de-teste",
        "ADMIN_USER": "cantina",
        "ADMIN_PASSWORD": "senha-teste",
        "RATELIMIT_ENABLED": False,
        "APP_ENV": "test",
    })
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def token(client):
    r = client.post("/api/auth/login", json={"username": "cantina", "senha": "senha-teste"})
    return r.get_json()["token"]


@pytest.fixture
def auth(token):
    return {"Authorization": f"Bearer {token}"}
