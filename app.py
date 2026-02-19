from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv

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

@app.get("/")
async def base_path():
    """
    Root endpoint to verify that the API is running.

    Returns:
        dict: A success message.
    """
    return {"success": True}

app.include_router(websocket_router)
app.include_router(user_router)
app.include_router(order_router)
app.include_router(products_router)
app.include_router(config_router)
app.include_router(slot_router)
app.include_router(table_router)
app.include_router(table_reservation_router)
