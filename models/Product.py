from pydantic import BaseModel
from typing import Optional

class Product(BaseModel):
    id: int
    product: str
    price: float
    name: str
