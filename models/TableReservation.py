from datetime import datetime
from pydantic import BaseModel
from models import Table

class TableReservation(BaseModel):
    customer_name: str
    seats: int
    start: datetime
    end: datetime
    table_id: int

    class Config:
        orm_mode = True

class TableReservationResponse(BaseModel):
    id: int
    customer_name: str
    seats: int
    start: datetime
    end: datetime
    table: Table

    class Config:
        orm_mode = True
