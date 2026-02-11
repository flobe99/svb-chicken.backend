from sqlalchemy import Column, Integer, String, DateTime
from models.OrderChickenDB import Base

class TableReservationDB(Base):
    __tablename__ = "table_reservations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    table_id = Column(Integer)
    customer_name = Column(String)
    seats = Column(Integer)
    start = Column(DateTime)
    end = Column(DateTime)
