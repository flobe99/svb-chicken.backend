from sqlalchemy import Column, Integer, String, Numeric
from models.Base import Base

class ProductDB(Base):
    __tablename__ = "price"

    id = Column(Integer, primary_key=True, index=True)
    product = Column(String)
    price = Column(Numeric(10, 2))
    name = Column(String)
