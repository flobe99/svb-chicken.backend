from sqlalchemy import Column, Integer, Text, Date, DateTime
from models.Base import Base

class SlotDB(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    range_start = Column(DateTime)
    range_end = Column(DateTime)
