from datetime import datetime
from pydantic import BaseModel, ConfigDict
from models import Table

class TableReservation(BaseModel):
    customer_name: str
    seats: int
    start: datetime
    end: datetime
    table_id: int

    model_config = ConfigDict(from_attributes=True)

class TableReservationResponse(BaseModel):
    id: int
    customer_name: str
    seats: int
    start: datetime
    end: datetime
    table: Table

    model_config = ConfigDict(from_attributes=True)
