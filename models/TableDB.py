from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from models.Base import Base

class TableDB(Base):
    __tablename__ = "table"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String)
    seats = Column(Integer)

    reservations = relationship("TableReservationDB", back_populates="table")