from datetime import datetime
from pydantic import BaseModel
from models import Table

class TableReservation(BaseModel):
    id: int
    customer_name: str
    seats: int
    start: datetime
    end: datetime
    table: Table

    class Config:
        orm_mode = True
