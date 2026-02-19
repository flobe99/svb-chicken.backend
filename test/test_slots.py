import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, datetime

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
# Helper: Slot anlegen
# ---------------------------------------------------------
def create_test_slot(db: Session, slot_date=date.today(), range_start=datetime(2023, 1, 1, 10, 0), range_end=datetime(2023, 1, 1, 12, 0)):
    slot = SlotDB(date=slot_date, range_start=range_start, range_end=range_end)
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot

# =========================================================
# TEST: GET /slots
# =========================================================
def test_get_all_slots():
    db = SessionLocal()
    create_test_slot(db, date(2023, 1, 1), datetime(2023, 1, 1, 10, 0), datetime(2023, 1, 1, 12, 0))
    create_test_slot(db, date(2023, 1, 2), datetime(2023, 1, 2, 14, 0), datetime(2023, 1, 2, 16, 0))

    response = client.get("/slots")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2

# =========================================================
# TEST: GET /slots/{id}
# =========================================================
def test_get_slot():
    db = SessionLocal()
    slot = create_test_slot(db, date(2023, 1, 1), datetime(2023, 1, 1, 10, 0), datetime(2023, 1, 1, 12, 0))

    response = client.get(f"/slots/{slot.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["date"] == "2023-01-01"

def test_get_slot_not_found():
    response = client.get("/slots/999")
    assert response.status_code == 404

# =========================================================
# TEST: POST /slots
# =========================================================
def test_create_slot():
    payload = {
        "date": "2023-01-01",
        "range_start": "2023-01-01T10:00:00",
        "range_end": "2023-01-01T12:00:00"
    }

    response = client.post("/slots", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True

# =========================================================
# TEST: PUT /slots/{id}
# =========================================================
def test_update_slot():
    db = SessionLocal()
    slot = create_test_slot(db, date(2023, 1, 1), datetime(2023, 1, 1, 10, 0), datetime(2023, 1, 1, 12, 0))

    payload = {
        "date": "2023-01-02",
        "range_start": "2023-01-02T14:00:00",
        "range_end": "2023-01-02T16:00:00"
    }

    response = client.put(f"/slots/{slot.id}", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True

def test_update_slot_not_found():
    payload = {
        "date": "2023-01-01",
        "range_start": "2023-01-01T10:00:00",
        "range_end": "2023-01-01T12:00:00"
    }

    response = client.put("/slots/999", json=payload)
    assert response.status_code == 404

# =========================================================
# TEST: DELETE /slots/{id}
# =========================================================
def test_delete_slot():
    db = SessionLocal()
    slot = create_test_slot(db, date(2023, 1, 1), datetime(2023, 1, 1, 10, 0), datetime(2023, 1, 1, 12, 0))

    response = client.delete(f"/slots/{slot.id}")
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_delete_slot_not_found():
    response = client.delete("/slots/999")
    assert response.status_code == 404