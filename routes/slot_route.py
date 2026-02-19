from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import asc
from sqlalchemy.orm import Session

from database import get_db
from models import *


slot_router = APIRouter(
    # prefix="/users",
    tags=["Config"]
)

@slot_router.get("/slots", tags=["Slot"])
def get_all_slots(db: Session = Depends(get_db)):
    
    try:
        slots = db.query(SlotDB).order_by(asc(SlotDB.range_start)).all()
        return [slot.__dict__ for slot in slots]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@slot_router.get("/slots/{id}", tags=["Slot"])
def get_slot(id: int, db: Session = Depends(get_db)):
    
    try:
        slot = db.query(SlotDB).filter(SlotDB.id == id).first()
        if not slot:
            raise HTTPException(status_code=404, detail="Slot not found")
        return slot.__dict__
    except Exception:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@slot_router.post("/slots", tags=["Slot"])
def create_slot(slot: Slot, db: Session = Depends(get_db)):
    
    try:
        new_slot = SlotDB(**slot.model_dump(exclude_unset=True))
        db.add(new_slot)
        db.commit()
        db.refresh(new_slot)
        return {"success": True, "created_slot": new_slot.__dict__}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@slot_router.put("/slots/{id}", tags=["Slot"])
def update_slot(id: int, slot: Slot, db: Session = Depends(get_db)):
    
    try:
        db_slot = db.query(SlotDB).filter(SlotDB.id == id).first()
        if not db_slot:
            raise HTTPException(status_code=404, detail="Slot not found")

        for field, value in slot.model_dump(exclude_unset=True).items():
            setattr(db_slot, field, value)

        db.commit()
        db.refresh(db_slot)
        return {"success": True, "updated_slot": db_slot.__dict__}
    except Exception:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@slot_router.delete("/slots/{id}", tags=["Slot"])
def delete_slot(id: int, db: Session = Depends(get_db)):
    
    try:
        db_slot = db.query(SlotDB).filter(SlotDB.id == id).first()
        if not db_slot:
            raise HTTPException(status_code=404, detail="Slot not found")

        db.delete(db_slot)
        db.commit()
        return {"success": True, "message": f"Slot with ID {id} deleted"}
    except Exception:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    