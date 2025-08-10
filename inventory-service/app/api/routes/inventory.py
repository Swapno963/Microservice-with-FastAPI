import logging
import httpx
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert, func
from sqlalchemy.exc import IntegrityError

from app.models.inventory import (
    InventoryItem,
    InventoryHistory,
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemResponse,
    InventoryCheck,
    InventoryReserve,
    InventoryRelease,
    InventoryAdjust,
)
from app.api.dependencies import get_current_user, is_admin
from app.db.postgresql import get_db
from app.services.product import product_service
from app.core.config import settings

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post("/", response_model=InventoryItemResponse, status_code=201)
async def create_inventory_item(
    item: InventoryItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(
        is_admin
    ),  # Only admins can create inventory
):
    """
    Create a new inventory item.

    This will:
    1. Verify the product exists
    2. Create the inventory record
    3. Create a history entry
    """
    # Verify the product exists
    product = await product_service.get_product(item.product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with ID {item.product_id} not found",
        )

    # Create inventory item
    db_item = InventoryItem(
        product_id=item.product_id,
        available_quantity=item.available_quantity,
        reserved_quantity=item.reserved_quantity,
        reorder_threshold=item.reorder_threshold,
    )

    try:
        db.add(db_item)
        await db.flush()  # Get the ID without committing

        # Add history record
        history_entry = InventoryHistory(
            product_id=item.product_id,
            quantity_change=item.available_quantity,
            previous_quantity=0,
            new_quantity=item.available_quantity,
            change_type="add",
            reference_id=None,
        )
        db.add(history_entry)

        await db.commit()
        await db.refresh(db_item)

        logger.info(f"Created inventory item for product {item.product_id}")
        return db_item
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Inventory item for product {item.product_id} already exists",
        )


@router.get("/", response_model=List[InventoryItemResponse])
async def get_inventory_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    low_stock_only: bool = Query(
        False, description="Filter to show only low stock items"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get all inventory items with optional filtering.
    """
    query = select(InventoryItem)

    if low_stock_only:
        query = query.where(
            InventoryItem.available_quantity <= InventoryItem.reorder_threshold
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return items


@router.get("/check", response_model=Dict[str, Any])
async def check_inventory(
    product_id: str = Query(..., description="Product ID to check"),
    quantity: int = Query(..., gt=0, description="Quantity to check"),
    db: AsyncSession = Depends(get_db),
):
    """
    Check if a product has sufficient available inventory.
    """
    query = select(InventoryItem).where(InventoryItem.product_id == product_id)
    result = await db.execute(query)
    item = result.scalars().first()

    if not item:
        return {
            "available": False,
            "message": f"Product {product_id} not found in inventory",
        }

    is_available = item.available_quantity >= quantity

    return {
        "available": is_available,
        "current_quantity": item.available_quantity,
        "requested_quantity": quantity,
        "product_id": product_id,
    }


@router.get("/{product_id}", response_model=InventoryItemResponse)
async def get_inventory_item(
    product_id: str = Path(..., description="The product ID"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get inventory for a specific product.
    """
    query = select(InventoryItem).where(InventoryItem.product_id == product_id)
    result = await db.execute(query)
    item = result.scalars().first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory for product {product_id} not found",
        )

    return item


@router.get("/{product_id}", response_model=InventoryItemResponse)
async def get_inventory_item(
    product_id: str = Path(..., description="THe Product ID"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get inventory for a specific product.
    """
    query = select(InventoryItem).where(InventoryItem.product_id == product_id)
    result = await db.execute(query)
    item = result.scalars().first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory for product {product_id} not found",
        )

    return item
