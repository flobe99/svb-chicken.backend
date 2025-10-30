from sqlalchemy import Column, Integer, String

from models.OrderChickenDB import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    password: str

class User(BaseModel):
    id: int
    username: str
    class Config:
        orm_mode = True
        
class Token(BaseModel):
    access_token: str
    token_type: str