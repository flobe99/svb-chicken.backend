from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    verifyed: bool

class User(BaseModel):
    id: int
    username: str
    email: EmailStr
    verifyed: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str