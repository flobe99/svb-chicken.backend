from sqlalchemy import Column, Integer, Text, Date, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class SlotDB(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(Text)
    date = Column(Date)
    range_start = Column(DateTime)
    range_end = Column(DateTime)
