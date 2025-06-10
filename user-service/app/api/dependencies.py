from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.postgresql import get_db
from app.models.users import User, TokenData
from app.core.security import verify_token
from typing import Optional
from sqlalchemy.future import select


# Define OAuth2 password flow for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_PREFIX}/auth/login", scheme_name="JWT"
)


# Get user by id
async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get a usesr by id"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """Get the current authenticated user based on the JWT token."""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # verify and decode the token
        payload = verify_token(token, "access")
        if payload is None:
            raise credentials_exception

        user_id = Optional[int] = (
            int(payload.get("sub")) if payload.get("sub") else None
        )
        if user_id is None:
            raise credentials_exception

        token_data = TokenData(user_id=user_id)

    except JWTError:
        raise credentials_exception

    # Get user for database
    user = await get_user_by_id(db, token_data.user_id)
    if user is None:
        raise credentials_exception

    # Check the user is active
    if not user._is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )

    return user
