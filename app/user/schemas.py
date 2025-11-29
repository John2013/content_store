from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    is_staff: bool


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserLogin(UserBase):
    password: str


class UserRead(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserInDB(UserRead):
    hashed_password: str


class UserUpdate(UserBase):
    is_active: bool = Field(default=True)
