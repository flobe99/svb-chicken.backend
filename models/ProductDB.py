from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Numeric

Base = declarative_base()

class ProductDB(Base):
    __tablename__ = "price"  # Tabellenname wie angegeben

    id = Column(Integer, primary_key=True, index=True)
    product = Column(String)
    price = Column(Numeric(10, 2))
