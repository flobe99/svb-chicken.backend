from sqlalchemy import Column, Integer, String, Boolean

from models.OrderChickenDB import Base

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    verifyed = Column(Boolean, unique=True, index=True)
