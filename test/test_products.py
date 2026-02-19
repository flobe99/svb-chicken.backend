import os
import pytest
from fastapi.testclient import TestClient

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
# Helper: Produkt anlegen
# ---------------------------------------------------------
def create_test_product(db, name="Chicken", price=5.0):
    product = ProductDB(product=name, name=name, price=price)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

# =========================================================
# TEST: GET /products
# =========================================================
def test_get_products():
    db = SessionLocal()
    create_test_product(db, "Chicken", 5.0)
    create_test_product(db, "Fries", 2.0)

    response = client.get("/products")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2
    assert data[0]["product"] == "Chicken"
    assert data[1]["product"] == "Fries"

# =========================================================
# TEST: GET /product/{id}
# =========================================================
def test_get_product_by_id():
    db = SessionLocal()
    product = create_test_product(db, "Nuggets", 3.0)

    response = client.get(f"/product/{product.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["product"] == "Nuggets"
    assert data["price"] == 3.0

def test_get_product_not_found():
    response = client.get("/product/999")
    assert response.status_code == 404

# =========================================================
# TEST: POST /product
# =========================================================
def test_create_product():
    payload = {
        "id": 0,
        "product": "Burger",
        "price": 6.5,
        "name": "Burger"
    }

    response = client.post("/product", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["product"] == "Burger"
    assert data["price"] == 6.5

# =========================================================
# TEST: PUT /product/{id}
# =========================================================
def test_update_product():
    db = SessionLocal()
    product = create_test_product(db, "OldName", 1.0)

    payload = {
        "id": product.id,
        "product": "NewName",
        "price": 9.99,
        "name": "NewName"
    }

    response = client.put(f"/product/{product.id}", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["product"]["product"] == "NewName"
    assert data["product"]["price"] == 9.99

def test_update_product_not_found():
    payload = {
        "id": 999,
        "product": "DoesNotExist",
        "price": 1.0,
        "name": "DoesNotExist"
    }

    response = client.put("/product/999", json=payload)
    assert response.status_code == 404

# =========================================================
# TEST: DELETE /product/{id}
# =========================================================
def test_delete_product():
    db = SessionLocal()
    product = create_test_product(db, "ToDelete", 4.0)

    response = client.delete(f"/product/{product.id}")
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_delete_product_not_found():
    response = client.delete("/product/999")
    assert response.status_code == 404
