from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import json

from models.OrderChicken import OrderChicken
from models.OrderChickenDB import OrderChickenDB

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

print("DATABASE_URL:", DATABASE_URL)


engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
# Base.metadata.create_all(bind=engine)

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
def create_order(order: OrderChicken):
    db = SessionLocal()
    db_order = OrderChickenDB(**order.dict())
    try:
        db.add(db_order)
        db.commit()
        return {"success": True}
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
async def update_order(id: str, updated_order: OrderChicken):
    db = SessionLocal()
    try:
        order = db.query(OrderChickenDB).filter(OrderChickenDB.id == id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        for key, value in updated_order.dict().items():
            setattr(order, key, value)

        db.commit()

        if updated_order.status in ["CHECKED_IN", "PAID", "READY_FOR_PICKUP"]:
            await broadcast_order_event(f"ORDER_{updated_order.status}", order.__dict__)

        return {"success": True}
    except Exception as e:
        db.rollback()
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
