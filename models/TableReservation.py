from pydantic import BaseModel
from datetime import datetime

class TableReservation(BaseModel):
    id: int
    table_id: int
    customer_name: str
    seats: int
    start: datetime
    end: datetime
