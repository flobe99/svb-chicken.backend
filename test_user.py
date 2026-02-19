import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Test-Umgebung setzen
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite://"

from app import app
from database import SessionLocal, get_db
from models import Base, UserDB
from auth import create_access_token,verify_token

client = TestClient(app)

# ---------------------------------------------------------
# DB Setup Fixture
# ---------------------------------------------------------
@pytest.fixture(autouse=True)
def setup_db():
    db = SessionLocal()
    Base.metadata.drop_all(bind=db.bind)
    Base.metadata.create_all(bind=db.bind)
    yield
    db.close()

# ---------------------------------------------------------
# Helper: User anlegen
# ---------------------------------------------------------
def create_test_user(db: Session, username="john", password="secret", verified=True):
    from auth import get_password_hash
    user = UserDB(
        username=username,
        email=f"{username}@mail.com",
        hashed_password=get_password_hash(password),
        verifyed=verified
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# =========================================================
# TEST: Registrierung
# =========================================================
def test_user_register():
    payload = {
        "username": "newuser",
        "email": "new@mail.com",
        "password": "pass123",
        "verifyed": False
    }

    response = client.post("/user/register", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@mail.com"
    assert data["verifyed"] is False

# =========================================================
# TEST: Login
# =========================================================
def test_user_login():
    db = SessionLocal()
    create_test_user(db, username="loginuser", password="mypw", verified=True)

    response = client.post(
        "/user/token",
        data={"username": "loginuser", "password": "mypw"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

# =========================================================
# TEST: Login verweigert, wenn nicht verifiziert
# =========================================================
def test_user_login_not_verified():
    db = SessionLocal()
    create_test_user(db, username="unverified", password="pw", verified=False)

    response = client.post(
        "/user/token",
        data={"username": "unverified", "password": "pw"}
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Account not verified"

# =========================================================
# TEST: /user/me
# =========================================================
def test_user_me():
    db = SessionLocal()
    user = create_test_user(db, username="meuser", password="pw", verified=True)

    token = create_access_token({"sub": user.username})

    response = client.get(
        "/user/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "meuser"

# =========================================================
# TEST: Passwort ändern
# =========================================================
def test_change_password():
    db = SessionLocal()
    create_test_user(db, username="changepw", password="oldpw", verified=True)

    response = client.post(
        "/user/change-password",
        params={
            "username": "changepw",
            "old_password": "oldpw",
            "new_password": "newpw"
        }
    )

    assert response.status_code == 200
    assert response.json()["msg"] == "Password updated successfully"

# =========================================================
# TEST: Passwort Reset
def test_reset_password(monkeypatch):
    db = SessionLocal()

    # get_db aus dem Router importieren
    from routes.user_route import get_db as router_get_db

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[router_get_db] = override_get_db

    # User anlegen
    create_test_user(db, username="resetuser", password="oldpw", verified=True)

    # verify_token aus auth importieren und mocken
    from auth import verify_token

    monkeypatch.setattr("routes.user_route.verify_token", lambda token: "resetuser")

    response = client.post(
        "/user/reset-password",
        params={"token": "dummy", "new_password": "newpw"}
    )

    assert response.status_code == 200
    assert response.json()["msg"] == "Password reset successfully"

    app.dependency_overrides.clear()
