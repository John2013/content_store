from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserLogin(UserBase):
    password: str


class UserRead(UserBase):
    id: int
    is_active: bool
    is_staff: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserInDB(UserRead):
    hashed_password: str


class UserUpdate(UserBase):
    is_active: bool = Field(default=True)
    is_staff: bool = Field(default=False)


class UserPatch(UserBase):
    email: str | None = None
    is_active: bool | None = None
    is_staff: bool | None = None
