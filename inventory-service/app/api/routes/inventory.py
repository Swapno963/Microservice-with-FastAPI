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
    InventoryReservation,
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemResponse,
    InventoryCheck,
    InventoryReserve,
    InventoryRelease,
    InventoryAdjust,
)
from app.api.dependencies import get_current_user, is_admin, require_service
from app.db.postgresql import get_db
from app.services.product import product_service
from app.core.config import settings

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="", tags=["inventory"])


@router.post("/", response_model=InventoryItemResponse, status_code=201)
async def create_inventory_item(
    item: InventoryItemCreate,
    db: AsyncSession = Depends(get_db),
    service: Dict[str, Any] = Depends(require_service),
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
    current_user: Dict[str, Any] = Depends(is_admin),
):
    """
    Update inventory item for a product using a row-level lock.
    """

    async with db.begin():

        # Lock inventory row
        result = await db.execute(
            select(InventoryItem)
            .where(InventoryItem.product_id == product_id)
            .with_for_update()
        )

        existing_item = result.scalars().first()

        if not existing_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory for product {product_id} not found",
            )

        previous_quantity = existing_item.available_quantity

        # Calculate new values
        new_available_quantity = (
            item_update.available_quantity
            if item_update.available_quantity is not None
            else existing_item.available_quantity
        )

        new_reserved_quantity = (
            item_update.reserved_quantity
            if item_update.reserved_quantity is not None
            else existing_item.reserved_quantity
        )

        new_reorder_threshold = (
            item_update.reorder_threshold
            if item_update.reorder_threshold is not None
            else existing_item.reorder_threshold
        )

        # Business validations

        if new_available_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Available quantity cannot be negative",
            )

        if new_reserved_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reserved quantity cannot be negative",
            )

        if new_reserved_quantity > new_available_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reserved quantity cannot exceed available quantity",
            )

        if new_reorder_threshold < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reorder threshold cannot be negative",
            )

        # Update ORM object directly
        existing_item.available_quantity = new_available_quantity
        existing_item.reserved_quantity = new_reserved_quantity
        existing_item.reorder_threshold = new_reorder_threshold
        existing_item.updated_at = func.now()

        # Create history record if quantity changed
        if previous_quantity != new_available_quantity:
            history_entry = InventoryHistory(
                product_id=product_id,
                quantity_change=new_available_quantity - previous_quantity,
                previous_quantity=previous_quantity,
                new_quantity=new_available_quantity,
                change_type="update",
                reference_id=None,
            )

            db.add(history_entry)

    # Transaction committed here

    await db.refresh(existing_item)

    # Outside transaction
    await check_and_notify_low_stock(existing_item)

    logger.info(f"Updated inventory for product {product_id}")

    return existing_item


@router.post("/reserve", response_model=Dict[str, Any])
async def reserve_inventory(
    reservation: InventoryReserve,
    db: AsyncSession = Depends(get_db),
    service: Dict[str, Any] = Depends(require_service),
):
    """
    Reserve inventory for an order.

    The inventory row is locked with SELECT ... FOR UPDATE. Counters and the
    reservation row commit together. A second call for the same order and
    product returns the existing hold.
    """
    async with db.begin():
        result = await db.execute(
            select(InventoryItem)
            .where(InventoryItem.product_id == reservation.product_id)
            .with_for_update()
        )
        item = result.scalars().first()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory for product {reservation.product_id} not found",
            )

        existing = None
        if reservation.order_id:
            existing_result = await db.execute(
                select(InventoryReservation)
                .where(
                    InventoryReservation.order_id == reservation.order_id,
                    InventoryReservation.product_id == reservation.product_id,
                )
                .with_for_update()
            )
            existing = existing_result.scalars().first()
            if existing and existing.status == "held":
                logger.info(
                    "Reserve already held for order %s product %s",
                    reservation.order_id,
                    reservation.product_id,
                )
                return {
                    "reserved": True,
                    "idempotent": True,
                    "product_id": reservation.product_id,
                    "quantity": existing.quantity,
                    "available_quantity": item.available_quantity,
                    "reserved_quantity": item.reserved_quantity,
                    "order_id": reservation.order_id,
                }

        if item.available_quantity < reservation.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient inventory. Requested: {reservation.quantity}, "
                    f"Available: {item.available_quantity}"
                ),
            )

        previous_available = item.available_quantity
        update_result = await db.execute(
            update(InventoryItem)
            .where(InventoryItem.id == item.id)
            .where(InventoryItem.available_quantity >= reservation.quantity)
            .values(
                available_quantity=InventoryItem.available_quantity
                - reservation.quantity,
                reserved_quantity=InventoryItem.reserved_quantity
                + reservation.quantity,
                updated_at=datetime.utcnow(),
            )
            .execution_options(synchronize_session="fetch")
        )
        if update_result.rowcount != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient inventory. Requested: {reservation.quantity}, "
                    f"Available: {item.available_quantity}"
                ),
            )
        await db.refresh(item)
        new_available = item.available_quantity
        new_reserved = item.reserved_quantity

        if existing:
            existing.quantity = reservation.quantity
            existing.status = "held"
            existing.expires_at = reservation.expires_at
            existing.updated_at = datetime.utcnow()
        elif reservation.order_id:
            db.add(
                InventoryReservation(
                    order_id=reservation.order_id,
                    product_id=reservation.product_id,
                    quantity=reservation.quantity,
                    status="held",
                    expires_at=reservation.expires_at,
                )
            )

        db.add(
            InventoryHistory(
                product_id=reservation.product_id,
                quantity_change=-reservation.quantity,
                previous_quantity=previous_available,
                new_quantity=new_available,
                change_type="reserve",
                reference_id=reservation.order_id,
            )
        )

    await check_and_notify_low_stock(item)

    logger.info(
        "Reserved %s units of product %s for order %s",
        reservation.quantity,
        reservation.product_id,
        reservation.order_id,
    )

    return {
        "reserved": True,
        "idempotent": False,
        "product_id": reservation.product_id,
        "quantity": reservation.quantity,
        "available_quantity": new_available,
        "reserved_quantity": new_reserved,
        "order_id": reservation.order_id,
    }


@router.post("/release", response_model=Dict[str, Any])
async def release_inventory(
    release: InventoryRelease,
    db: AsyncSession = Depends(get_db),
    service: Dict[str, Any] = Depends(require_service),
):
    """
    Release previously reserved inventory safely using row-level locking.
    """

    async with db.begin():
        result = await db.execute(
            select(InventoryItem)
            .where(InventoryItem.product_id == release.product_id)
            .with_for_update()
        )
        item = result.scalars().first()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory for product {release.product_id} not found",
            )

        reservation_row = None
        if release.order_id:
            reservation_result = await db.execute(
                select(InventoryReservation)
                .where(
                    InventoryReservation.order_id == release.order_id,
                    InventoryReservation.product_id == release.product_id,
                )
                .with_for_update()
            )
            reservation_row = reservation_result.scalars().first()
            if reservation_row is None or reservation_row.status != "held":
                logger.info(
                    "Release no-op for order %s product %s",
                    release.order_id,
                    release.product_id,
                )
                return {
                    "released": True,
                    "already_released": True,
                    "product_id": release.product_id,
                    "quantity": 0,
                    "available_quantity": item.available_quantity,
                    "reserved_quantity": item.reserved_quantity,
                    "order_id": release.order_id,
                }
            release_qty = reservation_row.quantity
        else:
            release_qty = release.quantity
            if item.reserved_quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No reserved inventory to release",
                )
            if release_qty > item.reserved_quantity:
                logger.warning(
                    "Release capped. Requested=%s, Reserved=%s",
                    release_qty,
                    item.reserved_quantity,
                )
                release_qty = item.reserved_quantity

        previous_available = item.available_quantity
        update_result = await db.execute(
            update(InventoryItem)
            .where(InventoryItem.id == item.id)
            .where(InventoryItem.reserved_quantity >= release_qty)
            .values(
                available_quantity=InventoryItem.available_quantity + release_qty,
                reserved_quantity=InventoryItem.reserved_quantity - release_qty,
                updated_at=datetime.utcnow(),
            )
            .execution_options(synchronize_session="fetch")
        )
        if update_result.rowcount != 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Reserved quantity changed before release could commit",
            )
        await db.refresh(item)

        if reservation_row is not None:
            reservation_row.status = "released"
            reservation_row.updated_at = datetime.utcnow()

        db.add(
            InventoryHistory(
                product_id=release.product_id,
                quantity_change=release_qty,
                previous_quantity=previous_available,
                new_quantity=item.available_quantity,
                change_type="release",
                reference_id=release.order_id,
            )
        )
        available_quantity = item.available_quantity
        reserved_quantity = item.reserved_quantity

    logger.info(
        "Released %s units of product %s for order %s",
        release_qty,
        release.product_id,
        release.order_id,
    )

    return {
        "released": True,
        "already_released": False,
        "product_id": release.product_id,
        "quantity": release_qty,
        "available_quantity": available_quantity,
        "reserved_quantity": reserved_quantity,
        "order_id": release.order_id,
    }


@router.post("/adjust", response_model=InventoryItemResponse)
async def adjust_inventory(
    adjustment: InventoryAdjust,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(is_admin),
):
    """
    Adjust inventory levels (add or remove) safely with row-level locking.
    """

    async with db.begin():

        # Lock row to prevent concurrent modifications
        result = await db.execute(
            select(InventoryItem)
            .where(InventoryItem.product_id == adjustment.product_id)
            .with_for_update()
        )

        item = result.scalars().first()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory for product {adjustment.product_id} not found",
            )

        previous_quantity = item.available_quantity

        # Calculate new quantity safely
        new_quantity = previous_quantity + adjustment.quantity_change

        # Business validation
        if new_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot reduce inventory below zero. "
                    f"Current={previous_quantity}, "
                    f"Adjustment={adjustment.quantity_change}"
                ),
            )

        # Apply update via ORM state change
        item.available_quantity = new_quantity
        item.updated_at = func.now()

        # Determine change type
        change_type = (
            "add"
            if adjustment.quantity_change > 0
            else "remove"
        )

        # Create history entry
        history_entry = InventoryHistory(
            product_id=adjustment.product_id,
            quantity_change=adjustment.quantity_change,
            previous_quantity=previous_quantity,
            new_quantity=new_quantity,
            change_type=change_type,
            reference_id=adjustment.reference_id,
        )

        db.add(history_entry)

    # Commit happens here

    await db.refresh(item)

    # Post-transaction side effect
    await check_and_notify_low_stock(item)

    logger.info(
        f"Adjusted inventory for product {adjustment.product_id} "
        f"by {adjustment.quantity_change}"
    )

    return item


@router.get("/low-stock", response_model=List[InventoryItemResponse])
async def get_low_stock_items(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get all items with inventory below their reorder threshold.
    """
    query = select(InventoryItem).where(
        InventoryItem.available_quantity <= InventoryItem.reorder_threshold
    )

    result = await db.execute(query)
    items = result.scalars().all()

    return items


@router.get("/history/{product_id}", response_model=List[Dict[str, Any]])
async def get_inventory_history(
    product_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get inventory history for a product.
    """
    # First check if product exists in inventory
    query = select(InventoryItem).where(InventoryItem.product_id == product_id)
    result = await db.execute(query)
    item = result.scalars().first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory for product {product_id} not found",
        )

    # Get history
    query = (
        select(InventoryHistory)
        .where(InventoryHistory.product_id == product_id)
        .order_by(InventoryHistory.timestamp.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    history = result.all()

    # Convert to list of dicts
    history_list = [
        {
            "id": h.id,
            "product_id": h.product_id,
            "quantity_change": h.quantity_change,
            "previous_quantity": h.previous_quantity,
            "new_quantity": h.new_quantity,
            "change_type": h.change_type,
            "reference_id": h.reference_id,
            "timestamp": h.timestamp,
        }
        for h in history
    ]

    return history_list


async def check_and_notify_low_stock(inventory_item: InventoryItem):
    """
    Check if an item is below its reorder threshold and send notification if needed.
    """
    if not settings.ENABLE_NOTIFICATIONS or not settings.NOTIFICATION_URL:
        return

    if inventory_item.available_quantity <= inventory_item.reorder_threshold:
        try:
            product = await product_service.get_product(inventory_item.product_id)
            product_name = (
                product.get("name", inventory_item.product_id)
                if product
                else inventory_item.product_id
            )

            notification_data = {
                "type": "low_stock",
                "product_id": inventory_item.product_id,
                "product_name": product_name,
                "current_quantity": inventory_item.available_quantity,
                "threshold": inventory_item.reorder_threshold,
                "timestamp": datetime.utcnow().isoformat(),
            }

            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    str(settings.NOTIFICATION_URL), json=notification_data
                )

            logger.info(
                f"Sent low stock notification for product {inventory_item.product_id}"
            )
        except Exception as e:
            logger.error(f"Failed to send low stock notification: {str(e)}")
