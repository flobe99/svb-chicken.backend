import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Test-Umgebung setzen
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite://"

from app import app
from database import SessionLocal, get_db
from models import *

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
# Helper: Config anlegen
# ---------------------------------------------------------
def create_test_config(db: Session, chicken=10, nuggets=20, fries=30):
    config = ConfigChickenDB(chicken=chicken, nuggets=nuggets, fries=fries)
    db.add(config)
    db.commit()
    db.refresh(config)
    return config

# =========================================================
# TEST: GET /config/{id}
# =========================================================
def test_get_config():
    db = SessionLocal()
    config = create_test_config(db, chicken=15, nuggets=25, fries=35)

    response = client.get(f"/config/{config.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["chicken"] == 15
    assert data["nuggets"] == 25
    assert data["fries"] == 35

def test_get_config_not_found():
    response = client.get("/config/999")
    assert response.status_code == 404

# =========================================================
# TEST: PUT /config/{id}
# =========================================================
def test_update_config():
    db = SessionLocal()
    config = create_test_config(db, chicken=10, nuggets=20, fries=30)

    payload = {
        "chicken": 12,
        "nuggets": 22,
        "fries": 32
    }

    response = client.put(f"/config/{config.id}", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["updated_config"]["chicken"] == 12
    assert data["updated_config"]["nuggets"] == 22
    assert data["updated_config"]["fries"] == 32

def test_update_config_not_found():
    payload = {
        "chicken": 1,
        "nuggets": 2,
        "fries": 3
    }

    response = client.put("/config/999", json=payload)
    assert response.status_code == 404

# =========================================================
# TEST: DELETE /config/{id}
# =========================================================
def test_delete_config():
    db = SessionLocal()
    config = create_test_config(db, chicken=5, nuggets=10, fries=15)

    response = client.delete(f"/config/{config.id}")
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_delete_config_not_found():
    response = client.delete("/config/999")
    assert response.status_code == 404