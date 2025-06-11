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
