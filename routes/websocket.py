from fastapi import APIRouter, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query, Depends, status
import json

websocket_router = APIRouter(
    # prefix="/chat",
    tags=["websocket"])

# WebSocket-Verbindungen
active_connections: list[WebSocket] = []

@websocket_router.websocket("/ws/orders")
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