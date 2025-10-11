from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import DateTime, cast, create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import json

from models.ConfigChicken import ConfigChicken
from models.ConfigChickenDB import ConfigChickenDB
from models.OrderChicken import OrderChicken
from models.OrderChickenDB import Base, OrderChickenDB
from models.Product import Product
from models.ProductDB import Base, ProductDB
from decimal import Decimal

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

        clean_order = jsonable_encoder(db_order)

        await broadcast_order_event(f"ORDER_{order.status}", clean_order)

        return {
            "success": True,
            "order": jsonable_encoder(db_order)
        }
    
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

@app.get("/orders/summary")
def get_order_summary(date: str = Query(...), interval: str = Query(...)):
    """
    Liefert die Summen für Hähnchen, Nuggets und Pommes für ein bestimmtes Datum und Zeitfenster.
    Beispiel:
    - date="2025-10-11"
    - interval="17:00-20:00"
    """
    try:
        db = SessionLocal()

        # Zeitfenster parsen
        try:
            start_str, end_str = interval.split("-")
            start_time = datetime.strptime(f"{date} {start_str}", "%Y-%m-%d %H:%M")
            end_time = datetime.strptime(f"{date} {end_str}", "%Y-%m-%d %H:%M")
        except Exception as e:
            raise HTTPException(status_code=400, detail="Ungültiges Zeitfenster")

        # Intervall alle 15 Minuten
        time_slots = []
        current = start_time
        while current <= end_time:
            time_slots.append(current)
            current += timedelta(minutes=15)

        # Datenbankabfrage
        orders = db.query(OrderChickenDB).filter(
            cast(OrderChickenDB.date, DateTime) >= start_time,
            cast(OrderChickenDB.date, DateTime) <= end_time
        ).all()

        # Aggregation
        result = []
        total_chicken = 0
        total_nuggets = 0
        total_fries = 0

        for slot in time_slots:
            slot_end = slot + timedelta(minutes=15)
            chicken_count = sum(order.chicken for order in orders if slot <= order.date < slot_end)
            nuggets_count = sum(order.nuggets for order in orders if slot <= order.date < slot_end)
            fries_count = sum(order.fries for order in orders if slot <= order.date < slot_end)

            total_chicken += chicken_count
            total_nuggets += nuggets_count
            total_fries += fries_count

            result.append({
                "time": slot.strftime("%H:%M"),
                "chicken": chicken_count,
                "nuggets": nuggets_count,
                "fries": fries_count
            })

        return {
            "date": date,
            "interval": interval,
            "slots": result,
            "total": {
                "chicken": total_chicken,
                "nuggets": total_nuggets,
                "fries": total_fries
            }
        }

    except Exception as e:
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
        
        if "checked_in_at" in updated_order.dict() and updated_order.checked_in_at is None:
            order.checked_in_at = None

        products = db.query(ProductDB).all()
        price_map = {p.product.lower(): float(p.price) for p in products}

        total_price = 0.0
        total_price += updated_order.chicken * price_map.get("chicken", 0)
        total_price += updated_order.nuggets * price_map.get("nuggets", 0)
        total_price += updated_order.fries * price_map.get("fries", 0)

        previous_status = order.status

        for key, value in updated_order.dict(exclude_unset=True).items():
            setattr(order, key, value)

        order.price = total_price

        if updated_order.status == "CHECKED_IN" and previous_status != "CHECKED_IN":
            order.checked_in_at = datetime.utcnow()

        db.commit()
        db.refresh(order)

        clean_order = jsonable_encoder(order)

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

@app.post("/order/price")
def calculate_order_price(order: OrderChicken):
    db = SessionLocal()
    try:
        products = db.query(ProductDB).all()
        price_map = {p.product.lower(): float(p.price) for p in products}

        total_price = 0.0
        total_price += order.chicken * price_map.get("chicken", 0)
        total_price += order.nuggets * price_map.get("nuggets", 0)
        total_price += order.fries * price_map.get("fries", 0)

        return {"price": round(total_price, 2)}
    except Exception as e:
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
        db.refresh(product)

        return {
            "success": True,
            "product": {
                "id": product.id,
                "product": product.product,
                "price": float(product.price)
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
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

from fastapi import Path

@app.post("/config")
async def create_config(config: ConfigChicken):
    db = SessionLocal()
    try:
        db_config = ConfigChickenDB(**config.dict(exclude={"id"}))
        db.add(db_config)
        db.commit()
        db.refresh(db_config)
        return {"success": True, "config": jsonable_encoder(db_config)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.put("/config/{config_id}")
async def update_config(config_id: int = Path(...), config: ConfigChicken = None):
    db = SessionLocal()
    try:
        db_config = db.query(ConfigChickenDB).filter(ConfigChickenDB.id == config_id).first()
        if not db_config:
            raise HTTPException(status_code=404, detail="Config not found")

        for field, value in config.dict(exclude_unset=True).items():
            setattr(db_config, field, value)

        db.commit()
        db.refresh(db_config)
        return {"success": True, "config": jsonable_encoder(db_config)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.delete("/config/{config_id}")
async def delete_config(config_id: int = Path(...)):
    db = SessionLocal()
    try:
        db_config = db.query(ConfigChickenDB).filter(ConfigChickenDB.id == config_id).first()
        if not db_config:
            raise HTTPException(status_code=404, detail="Config not found")

        db.delete(db_config)
        db.commit()
        return {"success": True, "message": f"Config with ID {config_id} deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
