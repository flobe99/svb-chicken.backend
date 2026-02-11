from pydantic import BaseModel

class Table(BaseModel):
    id: int
    name: str
    seats: int
