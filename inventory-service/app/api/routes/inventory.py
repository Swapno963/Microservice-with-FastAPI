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


@router.put("/{product_id}", response_model=InventoryItemResponse)
async def update_inventory_item(
    product_id: str,
    item_update: InventoryItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(
        is_admin
    ),  # Only admins can update inventory
):
    """
    Update inventory item for a product.
    """
    # Check if item exists
    query = select(InventoryItem).where(InventoryItem.product_id == product_id)
    result = await db.execute(query)
    existing_item = result.scalars().first()

    if not existing_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory for product {product_id} not found",
        )

    # Build update dictionary with only provided fields
    update_data = {}
    previous_quantity = existing_item.available_quantity

    if item_update.available_quantity is not None:
        update_data["available_quantity"] = item_update.available_quantity

    if item_update.reserved_quantity is not None:
        update_data["reserved_quantity"] = item_update.reserved_quantity

    if item_update.reorder_threshold is not None:
        update_data["reorder_threshold"] = item_update.reorder_threshold

    update_data["updated_at"] = func.now()

    # Update the item
    query = (
        update(InventoryItem)
        .where(InventoryItem.product_id == product_id)
        .values(**update_data)
        .returning(InventoryItem)
    )

    result = await db.execute(query)
    updated_item = result.scalars().first()

    # Add history record if quantity changed
    if "available_quantity" in update_data:
        quantity_change = update_data["available_quantity"] - previous_quantity
        history_entry = InventoryHistory(
            product_id=product_id,
            quantity_change=quantity_change,
            previous_quantity=previous_quantity,
            new_quantity=update_data["available_quantity"],
            change_type="update",
            reference_id=None,
        )
        db.add(history_entry)

    await db.commit()

    # Check for low stock and send notification if needed
    await check_and_notify_low_stock(updated_item)

    logger.info(f"Updated inventory for product {product_id}")
    return updated_item


@router.post("/reserve", response_model=Dict[str, Any])
async def reserve_inventory(
    reservation: InventoryReserve,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Reserve inventory for an order.

    This will:
    1. Check if inventory is available
    2. Reduce available quantity and increase reserved quantity
    3. Create a history entry
    """
    # Check if inventory exists and has sufficient quantity
    query = select(InventoryItem).where(
        InventoryItem.product_id == reservation.product_id
    )
    result = await db.execute(query)
    item = result.scalars().first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory for product {reservation.product_id} not found",
        )

    if item.available_quantity < reservation.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient inventory. Requested: {reservation.quantity}, Available: {item.available_quantity}",
        )

    # Update inventory
    new_available = item.available_quantity - reservation.quantity
    new_reserved = item.reserved_quantity + reservation.quantity

    query = (
        update(InventoryItem)
        .where(InventoryItem.product_id == reservation.product_id)
        .values(
            available_quantity=new_available,
            reserved_quantity=new_reserved,
            updated_at=func.now(),
        )
        .returning(InventoryItem)
    )

    result = await db.execute(query)
    updated_item = result.scalars().first()

    # Add history record
    history_entry = InventoryHistory(
        product_id=reservation.product_id,
        quantity_change=-reservation.quantity,
        previous_quantity=item.available_quantity,
        new_quantity=new_available,
        change_type="reserve",
        reference_id=reservation.order_id,
    )
    db.add(history_entry)

    await db.commit()

    # Check for low stock
    await check_and_notify_low_stock(updated_item)

    logger.info(
        f"Reserved {reservation.quantity} units of product {reservation.product_id}"
    )

    return {
        "reserved": True,
        "product_id": reservation.product_id,
        "quantity": reservation.quantity,
        "available_quantity": new_available,
        "reserved_quantity": new_reserved,
    }
