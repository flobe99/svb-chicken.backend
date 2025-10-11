from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, DateTime, Numeric

Base = declarative_base()

class ConfigChickenDB(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    chicken = Column(Integer)
    nuggets = Column(Integer)
    fries = Column(Integer)
