from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from app.models.users import User, UserBase, UserResponse, Address, AddressResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_current_user, get_db
from typing import List, Any, Dict, Optional
from sqlalchemy.future import select


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
