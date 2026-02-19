import os
from fastapi import Depends
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

# --- 1. ENV setzen ---
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite://"

# --- 2. App importieren ---
from app import app
from database import SessionLocal, get_db
from models import Base, OrderChickenDB, ProductDB

# --- 3. Tabellen erstellen ---
# Base.metadata.create_all(bind=engine)

client = TestClient(app)

# ------------------------------------
# Helper: Mock für Slot-Limits
# ------------------------------------
@pytest.fixture(autouse=True)
def mock_check_slot_limit(monkeypatch):
    monkeypatch.setattr(
        "routes.order_route.check_slot_limit",
        lambda *args, **kwargs: True
    )

# ------------------------------------
# Helper: Testproduktdaten
# ------------------------------------
@pytest.fixture(autouse=True)
def setup_products():
    db = SessionLocal()
    try:
        db.query(ProductDB).delete()   # optional: Tabelle leeren
        db.add(ProductDB(product="chicken", price=5.0))
        db.add(ProductDB(product="nuggets", price=3.0))
        db.add(ProductDB(product="fries", price=2.0))
        db.commit()
        yield
    finally:
        db.close()

@pytest.fixture(autouse=True)
def mock_side_effects(monkeypatch):
    # Broadcast Event Mock
    async def _noop(*args, **kwargs):
        return None
    monkeypatch.setattr(
        "routes.websocket.broadcast_order_event",
        _noop
    )

    yield

# ======================================================
# POST /order – Bestellung erstellen
# ======================================================
def test_create_order():
    payload = {
        "firstname": "John",
        "lastname": "Doe",
        "mail": "j@d.com",
        "phonenumber": "123",
        "date": "2025-10-10T17:00:00",
        "chicken": 2,
        "nuggets": 1,
        "fries": 3,
        "miscellaneous": "",
        "status": "CREATED",
        "price": 0,
        "checked_in_at": None
    }

    response = client.post("/order", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["order"]["price"] == 2 * 5 + 1 * 3 + 3 * 2  # 10 + 3 + 6 = 19


# ======================================================
# GET /orders – Liste abrufen
# ======================================================
def test_get_orders():
    response = client.get("/orders")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


# ======================================================
# GET /order/{id}
# ======================================================
def test_get_order():
    db = SessionLocal()
    try:
        order = OrderChickenDB(
            chicken=1, nuggets=1, fries=1
        )
        db.add(order)
        db.commit()
        oid = order.id
    finally:
        db.close()

    response = client.get(f"/order/{oid}")
    assert response.status_code == 200
    assert response.json()["id"] == oid


# ======================================================
# GET /order/{id} – not found
# ======================================================
def test_get_order_not_found():
    response = client.get("/order/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


# ======================================================
# POST /validate-order
# ======================================================
def test_validate_order():
    payload = {
        "firstname": "Max",
        "lastname": "Muster",
        "mail": "max@example.de",
        "phonenumber": "999",
        "date": "2025-11-20T18:00:00",
        "chicken": 1,
        "nuggets": 1,
        "fries": 1,
        "miscellaneous": "",
        "status": "CREATED",
        "price":0,
        "checked_in_at": None
    }

    response = client.post("/validate-order", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is True


# ======================================================
# POST /order/price
# ======================================================
def test_order_price():
    payload = {
        "firstname": "Test",
        "lastname": "User",
        "mail": "a@b.c",
        "phonenumber": "000",
        "date": "2025-10-11T17:00:00",
        "chicken": 1,
        "nuggets": 2,
        "fries": 1,
        "miscellaneous": "",
        "status": "CREATED",
        "price":0,
        "checked_in_at": None
    }

    response = client.post("/order/price", json=payload)
    assert response.status_code == 200
    assert response.json()["price"] == 1*5 + 2*3 + 1*2  # = 13


# ======================================================
# PUT /order/{id}
# ======================================================
def test_update_order():
    db = SessionLocal()
    try:
        order = OrderChickenDB(chicken=1, nuggets=1, fries=1, status="CREATED")
        db.add(order)
        db.commit()
        id = order.id
    finally:
        db.close()

    updated_payload = {
        "id": id,
        "firstname": "",
        "lastname": "",
        "mail": "",
        "phonenumber": "",
        "date": "2025-10-11T17:00:00",
        "chicken": 2,
        "nuggets": 0,
        "fries": 1,
        "miscellaneous": "",
        "status": "CHECKED_IN",
        "price":0,
        "checked_in_at": None
    }

    response = client.put(f"/order/{id}", json=updated_payload)
    assert response.status_code == 200

    data = response.json()
    assert data["order"]["chicken"] == 2
    assert data["order"]["status"] == "CHECKED_IN"


# ======================================================
# DELETE /order/{id}
# ======================================================
def test_delete_order():
    db = SessionLocal()
    try:
        order = OrderChickenDB(chicken=1, nuggets=1, fries=1)
        db.add(order)
        db.commit()
        oid = order.id
    finally:
        db.close()

    response = client.delete(f"/order/{oid}")
    assert response.status_code == 200
    assert response.json()["success"] is True

    # sicherstellen, dass gelöscht wurde
    response = client.get(f"/order/{oid}")
    assert response.status_code == 404