from pydantic import BaseModel, EmailStr
from typing import Optional


class UserBase(BaseModel):
    username: str
    first_name: str
    last_name: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    user_id: int

    class Config:
        from_attributes = True


class UserWithToken(BaseModel):
    user: UserRead
    access_token: str
    token_type: str = "bearer"


class UserUpdate(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[EmailStr]


class UserLogin(BaseModel):
    username: str
    password: str


class UserPassword(BaseModel):
    old_password: str
    new_password: str
