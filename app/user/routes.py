from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.db.session import get_db
from app.user import crud, schemas

router = APIRouter(prefix="/users", tags=["users"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.UserRead:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        user_id = int(sub)
    except (JWTError, ValueError):
        raise credentials_exception

    user = await crud.get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    return schemas.UserRead.model_validate(user)


def require_staff(
    current_user: schemas.UserRead = Depends(get_current_user),
) -> schemas.UserRead:
    """
    Dependency that requires the current user to be a staff member.
    """
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff privileges required",
        )
    return current_user


@router.post(
    "/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_in: schemas.UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.UserRead:
    existing = await crud.get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    hashed_password = get_password_hash(user_in.password)
    user = await crud.create_user(
        db, email=user_in.email, hashed_password=hashed_password
    )
    return schemas.UserRead.model_validate(user)


@router.post("/login")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = await crud.get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}


async def get_current_user_or_none(
    token: str | None = Depends(
        OAuth2PasswordBearer(tokenUrl="/api/users/login", auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
) -> schemas.UserRead | None:
    if not token:
        return None
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None


@router.get(
    "/", response_model=list[schemas.UserRead], dependencies=[Depends(require_staff)]
)
async def get_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: schemas.UserRead = Depends(get_current_user),
) -> list[schemas.UserRead]:
    return [schemas.UserRead.model_validate(user) for user in await crud.get_users(db)]


@router.get("/me", response_model=schemas.UserRead)
async def read_current_user(
    current_user: Annotated[schemas.UserRead, Depends(get_current_user)],
) -> schemas.UserRead:
    return current_user


@router.patch("/me", response_model=schemas.UserRead)
async def update_current_user(
    user_in: schemas.UserUpdate,
    current_user: Annotated[schemas.UserRead, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.UserRead:
    return schemas.UserRead.model_validate(
        await crud.update_user(db, current_user.id, user_in)
    )


@router.get(
    "/{user_id:int}",
    response_model=schemas.UserRead,
    dependencies=[Depends(require_staff)],
)
async def get_user(
    user_id: int,
    current_user: Annotated[schemas.UserRead, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.UserRead:
    user = await crud.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return schemas.UserRead.model_validate(user)


@router.put(
    "/{user_id:int}",
    response_model=schemas.UserRead,
    dependencies=[Depends(require_staff)],
)
async def update_user(
    user_id: int,
    user_in: schemas.UserUpdate,
    current_user: Annotated[schemas.UserRead, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.UserRead:
    user = await crud.update_user(db, user_id, user_in)
    return schemas.UserRead.model_validate(user)


@router.patch(
    "/{user_id:int}",
    response_model=schemas.UserRead,
    dependencies=[Depends(require_staff)],
)
async def patch_user(
    user_id: int,
    user_in: schemas.UserPatch,
    current_user: Annotated[schemas.UserRead, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.UserRead:
    user = await crud.patch_user(db, user_id, user_in)
    return schemas.UserRead.model_validate(user)


@router.delete(
    "/{user_id:int}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_staff)],
)
async def delete_user(
    user_id: int,
    current_user: Annotated[schemas.UserRead, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await crud.delete_user(db, user_id)
    return None
