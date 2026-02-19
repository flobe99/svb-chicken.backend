from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from models.Base import Base

class TableReservationDB(Base):
    __tablename__ = "table_reservation"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    table_id = Column(Integer, ForeignKey("table.id"))
    customer_name = Column(String)
    seats = Column(Integer)
    start = Column(DateTime)
    end = Column(DateTime)

    table = relationship("TableDB", back_populates="reservations")
