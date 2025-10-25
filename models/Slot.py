from pydantic import BaseModel
from datetime import date, datetime

class Slot(BaseModel):
    date: date
    range_start: datetime
    range_end: datetime
