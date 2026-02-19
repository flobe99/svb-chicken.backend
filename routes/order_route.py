
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException,Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import DateTime, cast
from sqlalchemy.orm import Session

from database import get_db
from models import *

from helper import check_slot_limit
from routes.websocket import broadcast_order_event

order_router = APIRouter(
    # prefix="/users",
    tags=["Order"]
)

@order_router.post("/order", tags=["Order"])
async def create_order(order: OrderChicken, db: Session = Depends(get_db)):
    """
    Creates a new order and calculates its total price.

    Args:
        order (OrderChicken): The order data submitted by the client.

    Returns:
        dict: A success flag and the created order with calculated price.
    """
    try:
        check_slot_limit(order, db)

        products = db.query(ProductDB).all()
        price_map = {p.product.lower(): float(p.price) for p in products}

        total_price = (
            order.chicken * price_map.get("chicken", 0) +
            order.nuggets * price_map.get("nuggets", 0) +
            order.fries * price_map.get("fries", 0)
        )

        db_order = OrderChickenDB(**{k: v for k, v in order.model_dump().items() if k != "id"})
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

@order_router.get("/orders", tags=["Order"])
def get_orders(status: str = Query(None), db: Session = Depends(get_db)):
    """
    Retrieves all orders, optionally filtered by status.

    Args:
        status (str, optional): Filter orders by their status.

    Returns:
        list: A list of order dictionaries.
    """
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

@order_router.get("/order/{id}", tags=["Order"])
def get_order(id: str, db: Session = Depends(get_db)):
    """
    Deletes an order by its ID.

    Args:
        id (str): The ID of the order to delete.

    Returns:
        dict: A success flag if deletion was successful.
    """
    try:
        order = db.query(OrderChickenDB).filter(OrderChickenDB.id == id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        return order

    except HTTPException:
        raise

    except Exception as e:
        print("Error in /orders:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@order_router.post("/validate-order", tags=["Order"])
def validate_order(order: OrderChicken, db: Session = Depends(get_db)):
    try:        
        check_slot_limit(order, db)

        return {"valid": True, "message": "Bestellung ist gültig"}

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail="Interner Serverfehler: " + str(e))
    finally:
        db.close()

@order_router.get("/orders/summary", tags=["Order"])
def get_order_summary(date: str = Query(...), interval: str = Query(...), db: Session = Depends(get_db)):
    """
    Liefert die Summen für Hähnchen, Nuggets und Pommes für ein bestimmtes Datum und Zeitfenster.
    Beispiel:
    - date="2025-10-11"
    - interval="17:00-20:00"
    """
    try:
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

@order_router.put("/order/{id}", tags=["Order"])
async def update_order(id: int, updated_order: OrderChicken, db: Session = Depends(get_db)):
    """
    Updates an existing order and recalculates its price.

    Args:
        id (int): The ID of the order to update.
        updated_order (OrderChicken): The updated order data.

    Returns:
        dict: A success flag and the updated order.
    """
    try:
        order = db.query(OrderChickenDB).filter(OrderChickenDB.id == id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        if updated_order.checked_in_at == "":
            order.checked_in_at = None
        

        products = db.query(ProductDB).all()
        price_map = {p.product.lower(): float(p.price) for p in products}

        total_price = 0.0
        total_price += updated_order.chicken * price_map.get("chicken", 0)
        total_price += updated_order.nuggets * price_map.get("nuggets", 0)
        total_price += updated_order.fries * price_map.get("fries", 0)

        previous_status = order.status

        for key, value in updated_order.model_dump(exclude_unset=True).items():
            setattr(order, key, value)

        check_slot_limit(order, db)

        order.price = total_price

        if updated_order.status == "CHECKED_IN" and previous_status != "CHECKED_IN":
            order.checked_in_at = datetime.now(UTC)

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
@order_router.delete("/order/{id}", tags=["Order"])
def delete_order(id: str, db: Session = Depends(get_db)):
    """
    Deletes an order by its ID.

    Args:
        id (str): The ID of the order to delete.

    Returns:
        dict: A success flag if deletion was successful.
    """
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

@order_router.post("/order/price", tags=["Order"])
def calculate_order_price(order: OrderChicken, db: Session = Depends(get_db)):
    """
    Calculates the total price of an order without saving it.

    Args:
        order (OrderChicken): The order data to price.

    Returns:
        dict: The calculated price.
    """
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
