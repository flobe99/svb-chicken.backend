import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

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
# Helper: Table anlegen
# ---------------------------------------------------------
def create_test_table(db: Session, name="Table 1", seats=4):
    table = TableDB(name=name, seats=seats)
    db.add(table)
    db.commit()
    db.refresh(table)
    return table

# --------------------------------------------------------- 
# Helper: Reservation anlegen
# ---------------------------------------------------------
def create_test_reservation(db: Session, customer_name="John Doe", seats=2, start=datetime(2023, 1, 1, 18, 0), end=datetime(2023, 1, 1, 20, 0), table_id=1):
    reservation = TableReservationDB(customer_name=customer_name, seats=seats, start=start, end=end, table_id=table_id)
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation

# =========================================================
# TEST: GET /tables
# =========================================================
def test_get_tables():
    db = SessionLocal()
    create_test_table(db, "Table 1", 4)
    create_test_table(db, "Table 2", 6)

    response = client.get("/tables")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2

# =========================================================
# TEST: GET /tables/{id}
# =========================================================
def test_get_table():
    db = SessionLocal()
    table = create_test_table(db, "Table 1", 4)

    response = client.get(f"/tables/{table.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Table 1"
    assert data["seats"] == 4

def test_get_table_not_found():
    response = client.get("/tables/999")
    assert response.status_code == 404

# =========================================================
# TEST: POST /tables
# =========================================================
def test_create_table():
    payload = {
        "id": 0,
        "name": "New Table",
        "seats": 8
    }

    response = client.post("/tables", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "New Table"
    assert data["seats"] == 8

# =========================================================
# TEST: PUT /tables/{id}
# =========================================================
def test_update_table():
    db = SessionLocal()
    table = create_test_table(db, "Old Name", 4)

    payload = {
        "id": table.id,
        "name": "New Name",
        "seats": 6
    }

    response = client.put(f"/tables/{table.id}", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["table"]["name"] == "New Name"
    assert data["table"]["seats"] == 6

def test_update_table_not_found():
    payload = {
        "id":999,
        "name": "DoesNotExist",
        "seats": 4
    }

    response = client.put("/tables/999", json=payload)
    assert response.status_code == 404

# =========================================================
# TEST: DELETE /tables/{id}
# =========================================================
def test_delete_table():
    db = SessionLocal()
    table = create_test_table(db, "ToDelete", 4)

    response = client.delete(f"/tables/{table.id}")
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_delete_table_not_found():
    response = client.delete("/tables/999")
    assert response.status_code == 404
