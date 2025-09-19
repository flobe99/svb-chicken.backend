from pydantic import BaseModel

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
