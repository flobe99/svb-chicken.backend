
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv


class OrderChickenDB(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)
    firstname = Column(String)
    lastname = Column(String)
    mail = Column(String)
    phonenumber = Column(String)
    date = Column(String)
    chicken = Column(Integer)
    nuggets = Column(Integer)
    fries = Column(Integer)
    miscellaneous = Column(String)

# Pydantic-Modell für Request
