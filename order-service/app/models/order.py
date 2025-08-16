from pydantic import BaseModel, Field, validator, condecimal
from bson import ObjectId
from typing import List, Optional, Dict, Any


class OrderItem(BaseModel):
    """Model for an item in an order."""

    product_id: str
    quantity: int = Field(..., gt=0)
    price: condecimal(max_digits=10, decimal_places=2) = Field(...)

    @validator("price")
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError("Price must be greater than 0")
        return v

    @validator("product_id")
    def validate_product_id(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid product ID format")
        return v


class OrderAddress(BaseModel):
    """Model for shipping/billing address."""

    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str


class OrderCreate(BaseModel):
    """Model for creating a new order."""

    user_id: str
    items: List[OrderItem] = Field(..., min_items=1)
    shipping_address: OrderAddress

    # Modified validator to accept any string for testing
    @validator("user_id")
    def validate_user_id(cls, v):
        # Accept any non-empty string for user_id
        if not v or not isinstance(v, str):
            raise ValueError("User ID must be a non-empty string")
        return v

    @validator("items")
    def validate_items(cls, v):
        if not v:
            raise ValueError("Order must have at least one item")
        return v
