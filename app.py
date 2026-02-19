# from datetime import UTC, datetime, timedelta
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query, Depends, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import DateTime, StaticPool, asc, cast, create_engine
from sqlalchemy.orm import Session, sessionmaker
import os
from dotenv import load_dotenv
import json

from auth import create_access_token, get_password_hash, verify_password, verify_token
from database import get_db
from models import *

load_dotenv()

from routes import *
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

##############################################################
@app.get("/")
async def base_path():
    """
    Root endpoint to verify that the API is running.

    Returns:
        dict: A success message.
    """
    return {"success": True}

##############################################################
app.include_router(websocket_router)
app.include_router(user_router)
app.include_router(order_router)
app.include_router(products_router)

@app.get("/config/{id}", tags=["Config"])
def get_config(id: int, db: Session = Depends(get_db)):
    
    try:
        product = db.query(ConfigChickenDB).filter(ConfigChickenDB.id == id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Config not found")
        return product.__dict__
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.put("/config/{id}", tags=["Config"])
def update_config(id: int, config: ConfigChicken = None, db: Session = Depends(get_db)):
    
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

@app.delete("/config/{id}", tags=["Config"])
def delete_config(id: int, db: Session = Depends(get_db)):
    
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

@app.get("/slots", tags=["Slot"])
def get_all_slots(db: Session = Depends(get_db)):
    
    try:
        slots = db.query(SlotDB).order_by(asc(SlotDB.range_start)).all()
        return [slot.__dict__ for slot in slots]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/slots/{id}", tags=["Slot"])
def get_slot(id: int, db: Session = Depends(get_db)):
    
    try:
        slot = db.query(SlotDB).filter(SlotDB.id == id).first()
        if not slot:
            raise HTTPException(status_code=404, detail="Slot not found")
        return slot.__dict__
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/slots", tags=["Slot"])
def create_slot(slot: Slot, db: Session = Depends(get_db)):
    
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

@app.put("/slots/{id}", tags=["Slot"])
def update_slot(id: int, slot: Slot, db: Session = Depends(get_db)):
    
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

@app.delete("/slots/{id}", tags=["Slot"])
def delete_slot(id: int, db: Session = Depends(get_db)):
    
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

@app.get("/tables-with-reservations", tags=["Table"])
def get_tables_with_reservations(db: Session = Depends(get_db)):
    """
    Retrieves all tables with their reservations.

    Returns:
        list: A list of tables, each containing an array of reservations.
    """
    
    try:
        tables = db.query(TableDB).order_by(TableDB.id.asc()).all()
        result = []
        for table in tables:
            reservations = db.query(TableReservationDB).filter(TableReservationDB.table_id == table.id).order_by(TableReservationDB.start.asc()).all()
            table_data = {
                "id": table.id,
                "name": table.name,
                "seats": table.seats,
                "reservations": [
                    {
                        "id": r.id,
                        "customer_name": r.customer_name,
                        "seats": r.seats,
                        "start": r.start,
                        "end": r.end
                    }
                    for r in reservations
                ]
            }
            result.append(table_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/tables", tags=["Table"])
def get_tables(db: Session = Depends(get_db)):
    
    try:
        tables = db.query(TableDB).order_by(TableDB.id.asc()).all()
        return [table.__dict__ for table in tables]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/tables/{id}", tags=["Table"])
def get_table(id: int, db: Session = Depends(get_db)):
    
    try:
        table = db.query(TableDB).filter(TableDB.id == id).first()
        if not table:
            raise HTTPException(status_code=404, detail="Table not found")
        return table.__dict__
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.post("/tables", tags=["Table"])
def create_table(table: Table, db: Session = Depends(get_db)):
    
    try:
        db_table = TableDB(**{k: v for k, v in table.dict().items() if k != "id"})
        db.add(db_table)
        db.commit()
        db.refresh(db_table)
        return db_table.__dict__
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.put("/tables/{id}", tags=["Table"])
def update_table(id: int, updated_table: Table, db: Session = Depends(get_db)):
    
    try:
        db_table = db.query(TableDB).filter(TableDB.id == id).first()
        if not db_table:
            raise HTTPException(status_code=404, detail="Table not found")

        for field, value in updated_table.dict(exclude_unset=True).items():
            setattr(db_table, field, value)

        db.commit()
        db.refresh(db_table)
        return {"success": True, "table": db_table.__dict__}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.delete("/tables/{id}", tags=["Table"])
def delete_table(id: int, db: Session = Depends(get_db)):
    
    try:
        db_table = db.query(TableDB).filter(TableDB.id == id).first()
        if not db_table:
            raise HTTPException(status_code=404, detail="Table not found")

        db.delete(db_table)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# TableReservation endpoints
@app.get("/table-reservations", tags=["TableReservation"])
def get_table_reservations(db: Session = Depends(get_db)):
    
    try:
        reservations = db.query(TableReservationDB).order_by(TableReservationDB.start.asc()).all()
        result = []
        for r in reservations:
            result.append({
                "id": r.id,
                "customer_name": r.customer_name,
                "seats": r.seats,
                "start": r.start,
                "end": r.end,
                "table": {
                    "id": r.table.id,
                    "name": r.table.name,
                    "seats": r.table.seats
                }
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/table-reservations/{id}", tags=["TableReservation"])
def get_table_reservation(id: int, db: Session = Depends(get_db)):
    
    try:
        reservation = db.query(TableReservationDB).filter(TableReservationDB.id == id).first()
        if not reservation:
            raise HTTPException(status_code=404, detail="Reservation not found")
        return {
            "id": reservation.id,
            "customer_name": reservation.customer_name,
            "seats": reservation.seats,
            "start": reservation.start,
            "end": reservation.end,
            "table": {
                "id": reservation.table.id,
                "name": reservation.table.name,
                "seats": reservation.table.seats
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.post("/table-reservations", tags=["TableReservation"])
def create_table_reservation(reservation: TableReservation, db: Session = Depends(get_db)):
    
    try:
        table = db.query(TableDB).filter(TableDB.id == reservation.table_id).first()
        if not table:
            raise HTTPException(status_code=400, detail="Table not found")

        db_res = TableReservationDB(**reservation.dict())
        db.add(db_res)
        db.commit()
        db.refresh(db_res)
        return {
            "success": True,
            "reservation": {
                "id": db_res.id,
                "customer_name": db_res.customer_name,
                "seats": db_res.seats,
                "start": db_res.start,
                "end": db_res.end,
                "table": {
                    "id": db_res.table.id,
                    "name": db_res.table.name,
                    "seats": db_res.table.seats
                }
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.put("/table-reservations/{id}", tags=["TableReservation"])
def update_table_reservation(id: int, updated_reservation: TableReservation, db: Session = Depends(get_db)):
    
    try:
        res = db.query(TableReservationDB).filter(TableReservationDB.id == id).first()
        if not res:
            raise HTTPException(status_code=404, detail="Reservation not found")

        if hasattr(updated_reservation, "table_id") and updated_reservation.table_id is not None:
            table = db.query(TableDB).filter(TableDB.id == updated_reservation.table_id).first()
            if not table:
                raise HTTPException(status_code=400, detail="Table not found")

        for field, value in updated_reservation.dict(exclude_unset=True).items():
            setattr(res, field, value)

        db.commit()
        db.refresh(res)
        return {
            "success": True,
            "reservation": {
                "id": res.id,
                "customer_name": res.customer_name,
                "seats": res.seats,
                "start": res.start,
                "end": res.end,
                "table": {
                    "id": res.table.id,
                    "name": res.table.name,
                    "seats": res.table.seats
                }
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.delete("/table-reservations/{id}", tags=["TableReservation"])
def delete_table_reservation(id: int, db: Session = Depends(get_db)):
    
    try:
        res = db.query(TableReservationDB).filter(TableReservationDB.id == id).first()
        if not res:
            raise HTTPException(status_code=404, detail="Reservation not found")

        db.delete(res)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

