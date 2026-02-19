from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import *

table_reservation_router = APIRouter(
    # prefix="/users",
    tags=["TableReservation"]
)

@table_reservation_router.get("/table-reservations", tags=["TableReservation"])
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


@table_reservation_router.get("/table-reservations/{id}", tags=["TableReservation"])
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
    except Exception:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@table_reservation_router.post("/table-reservations", tags=["TableReservation"])
def create_table_reservation(reservation: TableReservation, db: Session = Depends(get_db)):
    
    try:
        table = db.query(TableDB).filter(TableDB.id == reservation.table_id).first()
        if not table:
            raise HTTPException(status_code=400, detail="Table not found")

        db_res = TableReservationDB(**reservation.model_dump())
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
    except Exception:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@table_reservation_router.put("/table-reservations/{id}", tags=["TableReservation"])
def update_table_reservation(id: int, updated_reservation: TableReservation, db: Session = Depends(get_db)):
    
    try:
        res = db.query(TableReservationDB).filter(TableReservationDB.id == id).first()
        if not res:
            raise HTTPException(status_code=404, detail="Reservation not found")

        if hasattr(updated_reservation, "table_id") and updated_reservation.table_id is not None:
            table = db.query(TableDB).filter(TableDB.id == updated_reservation.table_id).first()
            if not table:
                raise HTTPException(status_code=400, detail="Table not found")

        for field, value in updated_reservation.model_dump(exclude_unset=True).items():
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
    except Exception:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@table_reservation_router.delete("/table-reservations/{id}", tags=["TableReservation"])
def delete_table_reservation(id: int, db: Session = Depends(get_db)):
    
    try:
        res = db.query(TableReservationDB).filter(TableReservationDB.id == id).first()
        if not res:
            raise HTTPException(status_code=404, detail="Reservation not found")

        db.delete(res)
        db.commit()
        return {"success": True}
    except Exception:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

