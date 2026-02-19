import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

from test.test_tables import create_test_reservation, create_test_table

# Test-Umgebung setzen
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite://"

from app import app
from database import SessionLocal, get_db
from models import *

client = TestClient(app)

# =========================================================
# TEST: GET /table-reservations
# =========================================================
def test_get_table_reservations():
    db = SessionLocal()
    table = create_test_table(db, "Table 1", 4)
    create_test_reservation(db, "John", 2, datetime(2023, 1, 1, 18, 0), datetime(2023, 1, 1, 20, 0), table.id)

    response = client.get("/table-reservations")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["customer_name"] == "John"

# =========================================================
# TEST: GET /table-reservations/{id}
# =========================================================
def test_get_table_reservation():
    db = SessionLocal()
    table = create_test_table(db, "Table 1", 4)
    reservation = create_test_reservation(db, "John", 2, datetime(2023, 1, 1, 18, 0), datetime(2023, 1, 1, 20, 0), table.id)

    response = client.get(f"/table-reservations/{reservation.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["customer_name"] == "John"
    assert data["table"]["name"] == "Table 1"

def test_get_table_reservation_not_found():
    response = client.get("/table-reservations/999")
    assert response.status_code == 404

# =========================================================
# TEST: POST /table-reservations
# =========================================================
def test_create_table_reservation():
    db = SessionLocal()
    table = create_test_table(db, "Table 1", 4)

    payload = {
        "customer_name": "Jane",
        "seats": 2,
        "start": "2023-01-01T19:00:00",
        "end": "2023-01-01T21:00:00",
        "table_id": table.id
    }

    response = client.post("/table-reservations", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["reservation"]["customer_name"] == "Jane"

def test_create_table_reservation_table_not_found():
    payload = {
        "customer_name": "Jane",
        "seats": 2,
        "start": "2023-01-01T19:00:00",
        "end": "2023-01-01T21:00:00",
        "table_id": 999
    }

    response = client.post("/table-reservations", json=payload)
    assert response.status_code == 400

# =========================================================
# TEST: PUT /table-reservations/{id}
# =========================================================
def test_update_table_reservation():
    db = SessionLocal()
    table = create_test_table(db, "Table 1", 4)
    reservation = create_test_reservation(db, "John", 2, datetime(2023, 1, 1, 18, 0), datetime(2023, 1, 1, 20, 0), table.id)

    payload = {
        "id": reservation.id,
        "start": "2026-02-19T21:20:01.363Z",
        "end": "2026-02-19T21:20:01.363Z",
        "customer_name": "John Updated",
        "seats": 3,
        "table_id": table.id
    }

    response = client.put(f"/table-reservations/{reservation.id}", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["reservation"]["customer_name"] == "John Updated"
    assert data["reservation"]["seats"] == 3

def test_update_table_reservation_not_found():
    payload = {
        "id": 999,
        "start": "2026-02-19T21:20:01.363Z",
        "end": "2026-02-19T21:20:01.363Z",
        "customer_name": "DoesNotExist",
        "seats": 3,
        "table_id": 1
    }

    response = client.put("/table-reservations/999", json=payload)
    assert response.status_code == 404

# =========================================================
# TEST: DELETE /table-reservations/{id}
# =========================================================
def test_delete_table_reservation():
    db = SessionLocal()
    table = create_test_table(db, "Table 1", 4)
    reservation = create_test_reservation(db, "John", 2, datetime(2023, 1, 1, 18, 0), datetime(2023, 1, 1, 20, 0), table.id)

    response = client.delete(f"/table-reservations/{reservation.id}")
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_delete_table_reservation_not_found():
    response = client.delete("/table-reservations/999")
    assert response.status_code == 404