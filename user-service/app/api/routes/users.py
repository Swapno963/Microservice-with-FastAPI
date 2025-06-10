from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_current_user, get_db
from typing import List, Any, Dict, Optional
from sqlalchemy.future import select
from app.models.users import (
    User,
    UserBase,
    UserResponse,
    Address,
    AddressResponse,
    UserUpdate,
)


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Any:
    """Get current user profile"""
    # Loading address explicitly to avoid lazy loading issue
    result = await db.execute(select(Address).where(Address.user_id == current_user.id))
    addresses = result.scalars().all()

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        addresses=[
            AddressResponse(
                id=addr.id,
                line1=addr.line1,
                line2=addr.line2,
                city=addr.city,
                state=addr.state,
                postal_code=addr.postal_code,
                country=addr.country,
                is_default=addr.is_default,
            )
            for addr in addresses
        ],
    )


# Update current user profile
@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Update current user profile"""
    # Update only provided fields
    update_data = user_update.dict(exclude_unset=True)

    if update_data:
        for key, value in update_data.items():
            setattr(current_user, key, value)

        await db.commit()
        await db.refresh(current_user)

        # Load addresses explicitly
    result = await db.execute(select(Address).where(Address.user_id == current_user.id))
    addresses = result.scalars().all()

    # Construct response manually
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        addresses=[
            AddressResponse(
                id=addr.id,
                line1=addr.line1,
                line2=addr.line2,
                city=addr.city,
                state=addr.state,
                postal_code=addr.postal_code,
                country=addr.country,
                is_default=addr.is_default,
            )
            for addr in addresses
        ],
    )
