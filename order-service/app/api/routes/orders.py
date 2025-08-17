from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body, status
import logging
from app.models.order import Order, OrderCreate, OrderUpdate, OrderResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.dependencies import get_db, get_current_user
from typing import List, Optional, Dict, Any
from app.services.user import user_service

# Configure logger
logger = logging.getLogger(__name__)


# Create router
router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order: OrderCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Create a new order.

    1. Verify the usesr exists.
    2. Verify all products exists and prices are correct.
    3. Check inventory availability for all the products.
    4. Reserve inventory for all the products.
    5. Create the order in the pending status

    """
    # Verify user exists
    user_valid = await user_service.verify_user(order.user_id)
    if not user_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID"
        )
