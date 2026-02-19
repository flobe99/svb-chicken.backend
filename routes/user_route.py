from fastapi import Depends, HTTPException, Query, APIRouter, status
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import UTC, datetime, timedelta
from sqlalchemy import DateTime, cast
from auth import create_access_token, get_password_hash, verify_password, verify_token
from database import SessionLocal, get_db
# from app import SessionLocal
from helper import check_slot_limit
from models import *
from routes.websocket import broadcast_order_event

user_router = APIRouter(
    # prefix="/users",
    tags=["User"]
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/token")

@user_router.post("/user/register", response_model=User, tags=["User"])
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    new_user = UserDB(username=user.username, email=user.email, hashed_password=hashed_password, verifyed=False)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@user_router.post("/user/token", response_model=Token, tags=["User"])
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.verifyed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not verified",
        )

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@user_router.post("/user/change-password", tags=["User"])
def change_password(username: str, old_password: str, new_password: str, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == username).first()
    if not user or not verify_password(old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if len(new_password.encode('utf-8')) > 72:
        raise HTTPException(status_code=400, detail="Password must not exceed 72 bytes.")
    user.hashed_password = get_password_hash(new_password[:72])
    db.commit()
    return {"msg": "Password updated successfully"}

@user_router.post("/user/reset-password", tags=["User"])
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user = db.query(UserDB).filter(UserDB.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if len(new_password.encode('utf-8')) > 72:
        raise HTTPException(status_code=400, detail="Password must not exceed 72 bytes.")
    user.hashed_password = get_password_hash(new_password[:72])
    db.commit()
    return {"msg": "Password reset successfully"}

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    username = verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(UserDB).filter(UserDB.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@user_router.get("/user/me", response_model=User, tags=["User"])
async def read_users_me(current_user: UserDB = Depends(get_current_user)):
    return current_user