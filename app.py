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

        clean_order = {
            k: float(v) if isinstance(v, Decimal) else v
            for k, v in db_order.__dict__.items()
            if not k.startswith("_")
        }

        await broadcast_order_event(f"ORDER_{order.status}", clean_order)

        return {
            "success": True,
            "order": {
                k: float(v) if isinstance(v, Decimal) else v
                for k, v in db_order.__dict__.items()
                if not k.startswith("_")
            }
        }
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
