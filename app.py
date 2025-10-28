from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import DateTime, asc, cast, create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import json

from models.ConfigChicken import ConfigChicken
from models.ConfigChickenDB import ConfigChickenDB
from models.LimitCode import LimitCode
from models.OrderChicken import OrderChicken
from models.OrderChickenDB import Base, OrderChickenDB
from models.Product import Product
from models.ProductDB import Base, ProductDB
from decimal import Decimal

from models.Slot import Slot
from models.SlotDB import SlotDB

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

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
    """
    WebSocket endpoint for receiving order events.

    Accepts a WebSocket connection and keeps it open until the client disconnects.
    Messages received from the client are ignored in this implementation.

    Args:
        websocket (WebSocket): The incoming WebSocket connection.
    """
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

async def broadcast_order_event(event_type: str, order_data: dict):
    """
    Broadcasts an order event to all active WebSocket connections.

    Sends a JSON-formatted message containing the event type and order data.

    Args:
        event_type (str): The type of event (e.g., "created", "updated").
        order_data (dict): The order data to be sent to clients.
    """
    message = json.dumps({
        "event": event_type,
        "data": order_data
    })
    for connection in active_connections:
        await connection.send_text(message)

@app.get("/")
async def base_path():
    """
    Root endpoint to verify that the API is running.

    Returns:
        dict: A success message.
    """
    return {"success": True}

def _check_slot_limit(order: OrderChicken, db):
    errors = []

    matching_slot = db.query(SlotDB).filter(
        SlotDB.range_start <= order.date,
        SlotDB.range_end >= order.date
    ).first()

    if not matching_slot:
        errors.append({
            "code": LimitCode.SLOT,
            "detail": "Bestellzeit liegt außerhalb der verfügbaren Slots"
        })

    if not _is_quarter_hour(order.date):
        errors.append({
            "code": LimitCode.TIME,
            "detail": "Uhrzeit muss auf eine Viertelstunde liegen (z. B. 12:15)"
        })

    config = db.query(ConfigChickenDB).first()
    if not config:
        raise HTTPException(status_code=500, detail="Keine Mengen-Konfiguration gefunden")

    slot_start = order.date.replace(minute=(order.date.minute // 15) * 15, second=0, microsecond=0)
    slot_end = slot_start + timedelta(minutes=15)

    orders_in_slot = db.query(OrderChickenDB).filter(
        OrderChickenDB.date >= slot_start,
        OrderChickenDB.date < slot_end
    ).all()

    used_chicken = sum(o.chicken for o in orders_in_slot)
    used_nuggets = sum(o.nuggets for o in orders_in_slot)
    used_fries = sum(o.fries for o in orders_in_slot)

    if used_chicken + order.chicken > config.chicken:
        errors.append({
            "code": LimitCode.CHICKEN,
            "detail": "Maximale Hähnchenmenge überschritten für dieses Zeitfenster."
        })
    if used_nuggets + order.nuggets > config.nuggets:
        errors.append({
            "code": LimitCode.NUGGETS,
            "detail": "Maximale Nuggetsmenge überschritten für dieses Zeitfenster."
        })
    if used_fries + order.fries > config.fries:
        errors.append({
            "code": LimitCode.FRIES,
            "detail": "Maximale Pommesmenge überschritten für dieses Zeitfenster."
        })

    if errors:
        raise HTTPException(status_code=400, detail={"success": False, "errors": errors})

@app.post("/order")
async def create_order(order: OrderChicken):
    """
    Creates a new order and calculates its total price.

    Args:
        order (OrderChicken): The order data submitted by the client.

    Returns:
        dict: A success flag and the created order with calculated price.
    """
    db = SessionLocal()
    try:
        _check_slot_limit(order, db)

        products = db.query(ProductDB).all()
        price_map = {p.product.lower(): float(p.price) for p in products}

        total_price = (
            order.chicken * price_map.get("chicken", 0) +
            order.nuggets * price_map.get("nuggets", 0) +
            order.fries * price_map.get("fries", 0)
        )

        db_order = OrderChickenDB(**{k: v for k, v in order.dict().items() if k != "id"})
        db_order.price = total_price

        db.add(db_order)
        db.commit()
        db.refresh(db_order)

        clean_order = jsonable_encoder(db_order)
        await broadcast_order_event(f"ORDER_{order.status}", clean_order)

        return {
            "success": True,
            "order": clean_order
        }

    except HTTPException as http_exc:
        db.rollback()
        raise http_exc

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/orders")
def get_orders(status: str = Query(None)):
    """
    Retrieves all orders, optionally filtered by status.

    Args:
        status (str, optional): Filter orders by their status.

    Returns:
        list: A list of order dictionaries.
    """
    db = SessionLocal()
    try:
        query = db.query(OrderChickenDB)
        if status:
            query = query.filter(OrderChickenDB.status == status)
        orders = query.all()
        return [order.__dict__ for order in orders]
    except Exception as e:
        print("Error in /orders:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/validate-order")
def validate_order(order: OrderChicken):
    db = SessionLocal()
    try:        
        _check_slot_limit(order, db)

        matching_slot = db.query(SlotDB).filter(
            SlotDB.range_start <= order.date,
            SlotDB.range_end >= order.date
        ).first()

        if not matching_slot:
            raise HTTPException(status_code=400, detail="Bestellzeit liegt außerhalb der verfügbaren Slots")

        return {"valid": True, "message": "Bestellung ist gültig", "slot_id": matching_slot.id}

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail="Interner Serverfehler: " + str(e))
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
    """
    Updates an existing order and recalculates its price.

    Args:
        id (int): The ID of the order to update.
        updated_order (OrderChicken): The updated order data.

    Returns:
        dict: A success flag and the updated order.
    """
    db = SessionLocal()
    try:
        order = db.query(OrderChickenDB).filter(OrderChickenDB.id == id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if updated_order.checked_in_at == "":
            order.checked_in_at = None

        _check_slot_limit(order, db)

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
    """
    Deletes an order by its ID.

    Args:
        id (str): The ID of the order to delete.

    Returns:
        dict: A success flag if deletion was successful.
    """
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
    """
    Calculates the total price of an order without saving it.

    Args:
        order (OrderChicken): The order data to price.

    Returns:
        dict: The calculated price.
    """
    db = SessionLocal()
    try:
        products = db.query(ProductDB).all()
        if order.checked_in_at == "":
            order.checked_in_at = None

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
    """
    Retrieves all available products.

    Returns:
        list: A list of product dictionaries.
    """
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
    """
    Retrieves a single product by its ID.

    Args:
        id (int): The ID of the product to retrieve.

    Returns:
        dict: The product data.
    """
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
    """
    Creates a new product entry.

    Args:
        product (Product): The product data to store.

    Returns:
        dict: The created product data.
    """
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
    """
    Updates an existing product.

    Args:
        id (int): The ID of the product to update.
        updated_product (Product): The new product data.

    Returns:
        dict: A success flag and the updated product data.
    """
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
    """
    Deletes a product by its ID.

    Args:
        id (int): The ID of the product to delete.

    Returns:
        dict: A success flag if deletion was successful.
    """
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

@app.get("/config/{id}")
def get_config(id: int):
    db = SessionLocal()
    try:
        product = db.query(ConfigChickenDB).filter(ConfigChickenDB.id == id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Config not found")
        return product.__dict__
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.put("/config/{id}")
def update_config(id: int, config: ConfigChicken = None):
    db = SessionLocal()
    try:
        db_config = db.query(ConfigChickenDB).filter(ConfigChickenDB.id == id).first()
        if not db_config:
            raise HTTPException(status_code=404, detail="Config not found")

        for field, value in config.dict(exclude_unset=True).items():
            setattr(db_config, field, value)

        db.commit()
        db.refresh(db_config)
        return {"success": True, "updated_config": db_config.__dict__}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.delete("/config/{id}")
def delete_config(id: int):
    db = SessionLocal()
    try:
        db_config = db.query(ConfigChickenDB).filter(ConfigChickenDB.id == id).first()
        if not db_config:
            raise HTTPException(status_code=404, detail="Config not found")

        db.delete(db_config)
        db.commit()
        return {"success": True, "message": f"Config with ID {id} deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/slots")
def get_all_slots():
    db = SessionLocal()
    try:
        slots = db.query(SlotDB).order_by(asc(SlotDB.range_start)).all()
        return [slot.__dict__ for slot in slots]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/slots/{id}")
def get_slot(id: int):
    db = SessionLocal()
    try:
        slot = db.query(SlotDB).filter(SlotDB.id == id).first()
        if not slot:
            raise HTTPException(status_code=404, detail="Slot not found")
        return slot.__dict__
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/slots")
def create_slot(slot: Slot):
    db = SessionLocal()
    try:
        new_slot = SlotDB(**slot.dict())
        db.add(new_slot)
        db.commit()
        db.refresh(new_slot)
        return {"success": True, "created_slot": new_slot.__dict__}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.put("/slots/{id}")
def update_slot(id: int, slot: Slot):
    db = SessionLocal()
    try:
        db_slot = db.query(SlotDB).filter(SlotDB.id == id).first()
        if not db_slot:
            raise HTTPException(status_code=404, detail="Slot not found")

        for field, value in slot.dict(exclude_unset=True).items():
            setattr(db_slot, field, value)

        db.commit()
        db.refresh(db_slot)
        return {"success": True, "updated_slot": db_slot.__dict__}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.delete("/slots/{id}")
def delete_slot(id: int):
    db = SessionLocal()
    try:
        db_slot = db.query(SlotDB).filter(SlotDB.id == id).first()
        if not db_slot:
            raise HTTPException(status_code=404, detail="Slot not found")

        db.delete(db_slot)
        db.commit()
        return {"success": True, "message": f"Slot with ID {id} deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

def _is_quarter_hour(dt: datetime) -> bool:
    return dt.minute in [0, 15, 30, 45]