from sqlalchemy import Column, Integer, String
from models.OrderChickenDB import Base

class TableDB(Base):
    __tablename__ = "tables"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String)
    seats = Column(Integer)
