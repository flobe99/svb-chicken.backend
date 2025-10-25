from pydantic import BaseModel
from datetime import date, datetime

class Slot(BaseModel):
    label: str
    date: date
    range_start: datetime
    range_end: datetime
