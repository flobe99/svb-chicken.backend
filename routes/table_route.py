# from fastapi import Depends, HTTPException, Query, APIRouter
# from sqlalchemy.orm import Session
# from fastapi.encoders import jsonable_encoder
# from datetime import UTC, datetime, timedelta
# from sqlalchemy import DateTime, cast,asc
# from database import SessionLocal, get_db
# # from app import SessionLocal
# from helper import check_slot_limit
# from models import *
# from routes.websocket import broadcast_order_event

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import *

table_router = APIRouter(
    # prefix="/users",
    tags=["Table"]
)

@table_router.get("/tables-with-reservations", tags=["Table"])
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


@table_router.get("/tables", tags=["Table"])
def get_tables(db: Session = Depends(get_db)):
    
    try:
        tables = db.query(TableDB).order_by(TableDB.id.asc()).all()
        return [table.__dict__ for table in tables]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@table_router.get("/tables/{id}", tags=["Table"])
def get_table(id: int, db: Session = Depends(get_db)):
    
    try:
        table = db.query(TableDB).filter(TableDB.id == id).first()
        if not table:
            raise HTTPException(status_code=404, detail="Table not found")
        return table.__dict__
    except Exception:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@table_router.post("/tables", tags=["Table"])
def create_table(table: Table, db: Session = Depends(get_db)):
    
    try:
        db_table = TableDB(**{k: v for k, v in table.model_dump().items() if k != "id"})
        db.add(db_table)
        db.commit()
        db.refresh(db_table)
        return db_table.__dict__
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@table_router.put("/tables/{id}", tags=["Table"])
def update_table(id: int, updated_table: Table, db: Session = Depends(get_db)):
    
    try:
        db_table = db.query(TableDB).filter(TableDB.id == id).first()
        if not db_table:
            raise HTTPException(status_code=404, detail="Table not found")

        for field, value in updated_table.model_dump(exclude_unset=True).items():
            setattr(db_table, field, value)

        db.commit()
        db.refresh(db_table)
        return {"success": True, "table": db_table.__dict__}
    except Exception:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@table_router.delete("/tables/{id}", tags=["Table"])
def delete_table(id: int, db: Session = Depends(get_db)):
    
    try:
        db_table = db.query(TableDB).filter(TableDB.id == id).first()
        if not db_table:
            raise HTTPException(status_code=404, detail="Table not found")

        db.delete(db_table)
        db.commit()
        return {"success": True}
    except Exception:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))