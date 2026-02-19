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
app.include_router(config_router)
app.include_router(slot_router)
app.include_router(table_router)
app.include_router(table_reservation_router)
