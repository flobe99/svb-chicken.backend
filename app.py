from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import json

from models.OrderChicken import OrderChicken
from models.OrderChickenDB import Base, OrderChickenDB
from models.Product import Product
from models.ProductDB import Base, ProductDB

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

print("DATABASE_URL:", DATABASE_URL)


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# WebSocket-Verbindungen
active_connections: list[WebSocket] = []

@app.websocket("/ws/orders")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

async def broadcast_order_event(event_type: str, order_data: dict):
    message = json.dumps({
        "event": event_type,
        "data": order_data
    })
    for connection in active_connections:
        await connection.send_text(message)

@app.get("/")
async def base_path():
    return {"success": True}

@app.post("/order")
async def create_order(order: OrderChicken):
    db = SessionLocal()
    try:
        products = db.query(ProductDB).all()
        price_map = {p.product.lower(): float(p.price) for p in products}

        total_price = 0.0
        total_price += order.chicken * price_map.get("chicken", 0)
        total_price += order.nuggets * price_map.get("nuggets", 0)
        total_price += order.fries * price_map.get("fries", 0)

        db_order = OrderChickenDB(**{k: v for k, v in order.dict().items() if k != "id"})
        db_order.price = total_price

        db.add(db_order)
        db.commit()
        db.refresh(db_order)

        await broadcast_order_event(f"ORDER_{order.status}", clean_order)

        return {"success": True, "order": db_order.__dict__}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/orders")
def get_orders(status: str = Query(None)):
    print("GET /orders called with status:", status)
    db = SessionLocal()
    try:
        query = db.query(OrderChickenDB)
        if status:
            query = query.filter(OrderChickenDB.status == status)
        orders = query.all()
        print("Orders fetched:", orders)
        return [order.__dict__ for order in orders]
    except Exception as e:
        print("Error in /orders:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.put("/order/{id}")
async def update_order(id: int, updated_order: OrderChicken):
    db = SessionLocal()
    try:
        order = db.query(OrderChickenDB).filter(OrderChickenDB.id == id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        products = db.query(ProductDB).all()
        price_map = {p.product.lower(): float(p.price) for p in products}

        total_price = 0.0
        total_price += updated_order.chicken * price_map.get("chicken", 0)
        total_price += updated_order.nuggets * price_map.get("nuggets", 0)
        total_price += updated_order.fries * price_map.get("fries", 0)

        for key, value in updated_order.dict().items():
            setattr(order, key, value)

        order.price = total_price

        db.commit()
        db.refresh(order)

        clean_order = {k: v for k, v in order.__dict__.items() if not k.startswith("_")}

        await broadcast_order_event(f"ORDER_{updated_order.status}", clean_order)

        return {"success": True, "order": clean_order}
    except Exception as e:
        db.rollback()
        print("Update error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# Bestellung löschen
@app.delete("/order/{id}")
def delete_order(id: str):
    db = SessionLocal()
    try:
        order = db.query(OrderChickenDB).filter(OrderChickenDB.id == id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        db.delete(order)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/products")
def get_products():
    db = SessionLocal()
    try:
        products = db.query(ProductDB).all()
        return [product.__dict__ for product in products]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/product/{id}")
def get_product(id: int):
    db = SessionLocal()
    try:
        product = db.query(ProductDB).filter(ProductDB.id == id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product.__dict__
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/product")
def create_product(product: Product):
    db = SessionLocal()
    db_product = ProductDB(**{k: v for k, v in product.dict().items() if k != "id"})
    try:
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product.__dict__
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.put("/product/{id}")
def update_product(id: int, updated_product: Product):
    db = SessionLocal()
    try:
        product = db.query(ProductDB).filter(ProductDB.id == id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        product.product = updated_product.product
        product.price = updated_product.price

        db.commit()
        return product.__dict__
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.delete("/product/{id}")
def delete_product(id: int):
    db = SessionLocal()
    try:
        product = db.query(ProductDB).filter(ProductDB.id == id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        db.delete(product)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
