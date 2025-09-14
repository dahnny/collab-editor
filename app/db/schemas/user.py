from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    password: str
    
class UserCreate(UserBase):
    phone_number: str | None = None
    
class UserResponse(BaseModel):
    id: str
    email: EmailStr
    created_at: datetime  # ISO format date string
    phone_number: str | None = None

    class Config:
        orm_mode = True  # This allows Pydantic to read data from ORM models
        
class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
    class Config:
        orm_mode = True