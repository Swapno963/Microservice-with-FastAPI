import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from app.models.product import ProductResponse, ProductCreate, PyObjectId, ProductUpdate
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.dependencies import get_db, get_current_user
from typing import List, Optional, Dict, Any
from app.services.inventory_service import inventory_service
from pymongo import ReturnDocument

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/products", tags=["Products"])


@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
    product: ProductCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Create a new product and automatically create inventory for it.
    """
    product_dict = product.dict()

    result = await db["PRODUCTS"].insert_one(product_dict)
    created_product = await db[:"products"].find_one({"_id": result.inserted_id})

    logger.info(f"Created product: {result.inserted_id}")

    # Automatically create inventory for the new product
    # try:
    #     # Use the product's quantity as the initial inventory
    #     inventory_created = await inventory_service.create_inventory(
    #         product_id=str(result.inserted_id),
    #         initial_quantity=product.quantity,
    #         reorder_threshold=max(5, int(product.quantity * 0.1))  # 10% of quantity or at least 5
    #     )

    #     if not inventory_created:
    #         logger.warning(f"Failed to create inventory for product {result.inserted_id}")
    #         # Note: We're still returning the product even if inventory creation failed
    #         # In a production system, you might want to handle this differently
    # except Exception as e:
    #     logger.error(f"Error creating inventory for product {result.inserted_id}: {str(e)}")

    return created_product


@router.get("/", response_model=List[ProductResponse])
async def get_products(
    skip: int = Query(0, ge=0, description="Number of products to skip"),
    limit: int = Query(
        100, ge=1, le=100, description="Max number of products to return"
    ),
    category: Optional[str] = Query(None, description="Filter by category"),
    name: Optional[str] = Query(None, description="Search by name (case insensitive)"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Get all products with optional filtering.
    """
    query = {}
    if category:
        query["category"] = category
    if name:
        query["name"] = {"$regex": name, "$options": "i"}  # Case insensative search
    if min_price is not None or max_price is not None:
        query["price"] = {}
        if min_price is not None:
            query["price"]["$gte"] = min_price
        if max_price is not None:
            query["price"]["$lte"] = max_price

    cursor = db["products"].find(query).skip(skip).limit(limit)
    products = await cursor.to_list(length=limit)

    return products
