from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, DateTime
from datetime import datetime

Base = declarative_base()

class OrderChickenDB(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)
    firstname = Column(String)
    lastname = Column(String)
    mail = Column(String)
    phonenumber = Column(String)
    date = Column(String)
    chicken = Column(Integer)
    nuggets = Column(Integer)
    fries = Column(Integer)
    miscellaneous = Column(String)
    status = Column(String, default="CREATED")
    created_at = Column(DateTime, default=datetime.utcnow)
