from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, DateTime, Numeric

Base = declarative_base()

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
