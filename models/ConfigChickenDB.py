from sqlalchemy import Column, String, Integer, DateTime, Numeric

from models.Base import Base

class ConfigChickenDB(Base):
    __tablename__ = "config"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    chicken = Column(Integer)
    nuggets = Column(Integer)
    fries = Column(Integer)
