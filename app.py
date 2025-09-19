
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

from fastapi.middleware.cors import CORSMiddleware
from models.OrderChicken import OrderChicken
from models.OrderChickenDB import OrderChickenDB

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


