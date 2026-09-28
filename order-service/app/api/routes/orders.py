from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Body, status
import hashlib
import logging
import time
from app.models.order import OrderCreate, OrderUpdate, OrderResponse, OrderStatusUpdate
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.dependencies import get_db, get_current_user
from typing import List, Optional, Dict, Any
from app.services.user import user_service
from app.services.product import product_service
from app.core.config import settings
from app.queue import RELEASE_QUEUE, enqueue_release, enqueue_reserve, get_redis, lock_key
from bson import ObjectId
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

# Configure logger
logger = logging.getLogger(__name__)


# Create router
router = APIRouter(prefix="", tags=["orders"])


def _redis_or_503():
    redis = get_redis()
    if redis is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reservation queue is unavailable",
        )
    return redis


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_order(
    order: OrderCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
):
    """
    Create a pending order and enqueue reservation.

    The handler does not call inventory. The worker reserves stock and retries.
    """
    # Verify user exists
    user_id = str(current_user["sub"])
    request_hash = hashlib.sha256(
        order.json(sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    existing_order = await db["orders"].find_one(
        {"user_id": user_id, "idempotency_key": idempotency_key}
    )
    if existing_order:
        if existing_order.get("request_hash") != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key was already used for a different order",
            )
        return existing_order

    user_valid = await user_service.verify_user(user_id)
    if not user_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID"
        )

    # Verify all products exist and prices are correct
    products_valid = await product_service.verify_products(order.items)
    if not products_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more products are invalid or have incorrect prices",
        )

    # Calculate total price
    total_price = sum(Decimal(str(item.price)) * item.quantity for item in order.items)

    # Create the order
    now = datetime.now(timezone.utc)
    reservation_expires_at = now + timedelta(seconds=settings.RESERVATION_TTL_SECONDS)

    # Convert order items to dictionary format, explicitly converting Decimal to float
    items_dict = []
    for item in order.items:
        items_dict.append(
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price": float(item.price),  # Convert Decimal to float for MongoDB
            }
        )

    order_dict = {
        "user_id": user_id,
        "idempotency_key": idempotency_key,
        "request_hash": request_hash,
        "items": items_dict,
        "total_price": float(total_price),  # Convert Decimal to float for MongoDB
        "status": settings.ORDER_STATUS["PENDING"],
        "reservation_state": "pending",
        "reserve_attempts": 0,
        "reservation_expires_at": reservation_expires_at,
        "shipping_address": order.shipping_address.dict(),
        "created_at": now,
        "updated_at": now,
    }

    try:
        result = await db["orders"].insert_one(order_dict)
    except DuplicateKeyError:
        existing_order = await db["orders"].find_one(
            {"user_id": user_id, "idempotency_key": idempotency_key}
        )
        if (
            existing_order
            and existing_order.get("request_hash") == request_hash
        ):
            return existing_order
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency key was already used for a different order",
        )
    order_id = str(result.inserted_id)

    try:
        await enqueue_reserve(_redis_or_503(), order_id)
    except HTTPException:
        await db["orders"].delete_one({"_id": result.inserted_id})
        raise
    except Exception:
        await db["orders"].delete_one({"_id": result.inserted_id})
        logger.exception("Failed to enqueue reservation for order %s", order_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not queue reservation",
        )

    created_order = await db["orders"].find_one({"_id": result.inserted_id})

    logger.info("Created pending order %s", order_id)
    return created_order


@router.get("/", response_model=List[OrderResponse])
async def get_orders(
    skip: int = Query(0, ge=0, description="Number of orders to skip"),
    limit: int = Query(10, ge=1, le=100, description="Max number of orders to return"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get all orders with optional filtering.

    This endpoint allows filtering by:
    - Order status
    - User ID
    - Date range
    """
    query = {}
    if not current_user.get("is_admin", False):
        query["user_id"] = str(current_user["sub"])

    # Apply filters if provided
    if status:
        if status not in settings.ORDER_STATUS.values():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(settings.ORDER_STATUS.values())}",
            )
        query["status"] = status

    if user_id:
        if not current_user.get("is_admin", False) and user_id != str(
            current_user["sub"]
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own orders",
            )
        query["user_id"] = user_id

    # Date filtering
    date_filter = {}
    if start_date:
        try:
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            date_filter["$gte"] = start_datetime
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use YYYY-MM-DD",
            )

    if end_date:
        try:
            # Add a day to include the entire end date
            end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
            end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
            date_filter["$lte"] = end_datetime
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use YYYY-MM-DD",
            )

    if date_filter:
        query["created_at"] = date_filter

    # Run the query
    cursor = db["orders"].find(query).sort("created_at", -1).skip(skip).limit(limit)
    orders = await cursor.to_list(length=limit)

    return orders


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str = Path(..., description="The ID of the order to retrieve"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get a single order by ID.
    """
    # Validate the order ID
    if not ObjectId.is_valid(order_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order ID format"
        )

    order = await db["orders"].find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found",
        )
    if (
        not current_user.get("is_admin", False)
        and order["user_id"] != str(current_user["sub"])
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found",
        )

    return order


@router.get("/user/{user_id}", response_model=List[OrderResponse])
async def get_user_orders(
    user_id: str = Path(..., description="User ID to get orders for"),
    skip: int = Query(0, ge=0, description="Number of orders to skip"),
    limit: int = Query(10, ge=1, le=100, description="Max number of orders to return"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get all orders for a specific user.
    """
    if (
        not current_user.get("is_admin", False)
        and user_id != str(current_user["sub"])
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own orders",
        )

    # Build the query
    query = {"user_id": user_id}

    if status:
        if status not in settings.ORDER_STATUS.values():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(settings.ORDER_STATUS.values())}",
            )
        query["status"] = status

    # Run the query
    cursor = db["orders"].find(query).sort("created_at", -1).skip(skip).limit(limit)
    orders = await cursor.to_list(length=limit)

    return orders


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    status_update: OrderStatusUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Update the status of an order.

    Cancelling enqueues a release. The worker calls inventory.
    """
    # Validate the order ID
    if not ObjectId.is_valid(order_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order ID format"
        )

    # Get the current order
    order = await db["orders"].find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found",
        )
    if (
        not current_user.get("is_admin", False)
        and order["user_id"] != str(current_user["sub"])
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found",
        )

    current_status = order["status"]
    new_status = status_update.status
    if not current_user.get("is_admin", False) and new_status != "cancelled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customers can only cancel orders",
        )
    if new_status == settings.ORDER_STATUS["PAID"]:
        if order.get("reservation_state") != "reserved":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An order can only be marked paid while stock is reserved",
            )
        expires_at = order.get("reservation_expires_at")
        if expires_at and expires_at <= datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The stock reservation has expired",
            )

    # Check if the status transition is allowed
    if new_status not in settings.ALLOWED_STATUS_TRANSITIONS.get(current_status, []):
        allowed = settings.ALLOWED_STATUS_TRANSITIONS.get(current_status, [])
        allowed_str = ", ".join(allowed) if allowed else "none"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from '{current_status}' to '{new_status}'. Allowed transitions: {allowed_str}",
        )

    cancel_statuses = [
        settings.ORDER_STATUS["PENDING"],
        settings.ORDER_STATUS["PAID"],
        settings.ORDER_STATUS["PROCESSING"],
    ]
    should_release = (
        new_status == settings.ORDER_STATUS["CANCELLED"]
        and current_status in cancel_statuses
    )

    redis = _redis_or_503()
    payment_lock = False
    if new_status == settings.ORDER_STATUS["PAID"]:
        payment_lock = bool(
            await redis.set(lock_key(order_id), "status-update", nx=True, ex=30)
        )
        if not payment_lock:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Reservation is being updated. Try again.",
            )

    try:
        updated_order = await db["orders"].find_one_and_update(
            {"_id": ObjectId(order_id), "status": current_status},
            {"$set": {"status": new_status, "updated_at": datetime.utcnow()}},
            return_document=ReturnDocument.AFTER,
        )
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Order status changed. Refresh and try again.",
            )
        if new_status == settings.ORDER_STATUS["PAID"]:
            await redis.zrem(RELEASE_QUEUE, order_id)
    finally:
        if payment_lock:
            await redis.delete(lock_key(order_id))

    if should_release:
        try:
            await enqueue_release(redis, order_id, time.time())
        except HTTPException:
            raise
        except Exception:
            logger.exception("Failed to enqueue release for order %s", order_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Order was cancelled but the release could not be queued",
            )

    logger.info(
        f"Updated order {order_id} status from {current_status} to {new_status}"
    )
    return updated_order


@router.delete("/{order_id}", status_code=204)
async def cancel_order(
    order_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Cancel an order (if not shipped).

    This will set the order status to cancelled and enqueue a stock release.
    """
    # Validate the order ID
    if not ObjectId.is_valid(order_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order ID format"
        )

    # Get the current order
    order = await db["orders"].find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found",
        )
    if (
        not current_user.get("is_admin", False)
        and order["user_id"] != str(current_user["sub"])
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found",
        )

    current_status = order["status"]

    if (
        current_status == settings.ORDER_STATUS["CANCELLED"]
        and order.get("reservation_state") == "reserved"
    ):
        try:
            await enqueue_release(_redis_or_503(), order_id, time.time())
        except HTTPException:
            raise
        except Exception:
            logger.exception("Failed to requeue release for order %s", order_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not queue reservation release",
            )
        return None

    # Check if the order can be cancelled
    non_cancellable = [
        settings.ORDER_STATUS["SHIPPED"],
        settings.ORDER_STATUS["DELIVERED"],
        settings.ORDER_STATUS["CANCELLED"],
        settings.ORDER_STATUS["REFUNDED"],
    ]

    if current_status in non_cancellable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order in '{current_status}' status",
        )

    # Update the order status to cancelled
    await db["orders"].update_one(
        {"_id": ObjectId(order_id)},
        {
            "$set": {
                "status": settings.ORDER_STATUS["CANCELLED"],
                "updated_at": datetime.utcnow(),
            }
        },
    )

    try:
        await enqueue_release(_redis_or_503(), order_id, time.time())
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to enqueue release for order %s", order_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Order was cancelled but the release could not be queued",
        )

    logger.info(f"Cancelled order {order_id}")
    return None
