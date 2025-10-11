from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class ConfigChicken(BaseModel):
    id: Optional[int] = None
    chicken: int
    nuggets: int
    fries: int

