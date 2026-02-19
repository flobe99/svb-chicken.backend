from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import *


config_router = APIRouter(
    # prefix="/users",
    tags=["Config"]
)

@config_router.get("/config/{id}", tags=["Config"])
def get_config(id: int, db: Session = Depends(get_db)):
    
    try:
        product = db.query(ConfigChickenDB).filter(ConfigChickenDB.id == id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Config not found")
        return product.__dict__
    except Exception:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@config_router.put("/config/{id}", tags=["Config"])
def update_config(id: int, config: ConfigChicken = None, db: Session = Depends(get_db)):
    
    try:
        db_config = db.query(ConfigChickenDB).filter(ConfigChickenDB.id == id).first()
        if not db_config:
            raise HTTPException(status_code=404, detail="Config not found")

        for field, value in config.model_dump(exclude_unset=True).items():
            setattr(db_config, field, value)

        db.commit()
        db.refresh(db_config)
        return {"success": True, "updated_config": db_config.__dict__}
    except Exception:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@config_router.delete("/config/{id}", tags=["Config"])
def delete_config(id: int, db: Session = Depends(get_db)):
    
    try:
        db_config = db.query(ConfigChickenDB).filter(ConfigChickenDB.id == id).first()
        if not db_config:
            raise HTTPException(status_code=404, detail="Config not found")

        db.delete(db_config)
        db.commit()
        return {"success": True, "message": f"Config with ID {id} deleted"}
    except Exception:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))