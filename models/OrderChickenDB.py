from models.Base import Base
from sqlalchemy import Column, String, Integer, DateTime, Numeric

class OrderChickenDB(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    firstname = Column(String)
    lastname = Column(String)
    mail = Column(String)
    phonenumber = Column(String)
    date = Column(DateTime)
    chicken = Column(Integer)
    nuggets = Column(Integer)
    fries = Column(Integer)
    miscellaneous = Column(String)
    status = Column(String, default="CREATED")
    price = Column(Numeric(10, 2))
    checked_in_at = Column(DateTime)
