from typing import Optional, Any, Coroutine, Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.user.models import User
from app.user import schemas


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    hashed_password: str,
    is_active: bool = True,
    is_staff: bool = False,
) -> User:
    user = User(
        email=email,
        hashed_password=hashed_password,
        is_active=is_active,
        is_staff=is_staff,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    await db.refresh(user)
    return user


async def get_users(db: AsyncSession) -> Sequence[User]:
    result = await db.execute(select(User))
    return result.scalars().all()


async def update_user(
    db: AsyncSession,
    user_id: int,
    user_in: schemas.UserUpdate,
) -> User:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    user.email = user_in.email
    user.is_active = user_in.is_active
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(
    db: AsyncSession,
    user_id: int,
) -> None:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    await db.delete(user)
    await db.commit()
