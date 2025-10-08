from pydantic import BaseModel
from typing import Optional
from enum import Enum

class OrderStatus(str, Enum):
    CREATED = "CREATED"
    CHECKED_IN = "CHECKED_IN"
    PAID = "PAID"
    PRINTED = "PRINTED"
    PREPARING = "PREPARING"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class OrderChicken(BaseModel):
    id: str
    firstname: str
    lastname: str
    mail: str
    phonenumber: str
    date: str
    chicken: int
    nuggets: int
    fries: int
    miscellaneous: str
    status: OrderStatus = OrderStatus.CREATED
