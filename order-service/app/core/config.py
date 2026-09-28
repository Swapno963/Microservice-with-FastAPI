import os
from typing import Optional, Dict, Any, List

from pydantic import BaseSettings, AnyHttpUrl, validator


class Settings(BaseSettings):
    # API settings
    API_PREFIX: str = "/api/v1/orders"
    DEBUG: bool = False
    PROJECT_NAME: str = "Order Service"
    PORT: int = 8001
    CORS_ORIGIN: str = "http://localhost:8080"
    
    # MongoDB settings
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "order_db"
    
    # Service URLs
    USER_SERVICE_URL: AnyHttpUrl
    PRODUCT_SERVICE_URL: AnyHttpUrl
    INVENTORY_SERVICE_URL: AnyHttpUrl
    
    # Retry Configuration
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 1  # seconds

    # Reservation worker
    REDIS_URL: str = "redis://localhost:6379/0"
    RESERVATION_TTL_SECONDS: int = 900
    MAX_RESERVE_ATTEMPTS: int = 5
    RESERVE_BACKOFF_SECONDS: List[int] = [5, 15, 45, 45, 45]
    
    # Authentication shared with the user service.
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    INTERNAL_SERVICE_TOKEN: str
    
    # Order status codes
    ORDER_STATUS: Dict[str, str] = {
        "PENDING": "pending",
        "PAID": "paid",
        "PROCESSING": "processing",
        "SHIPPED": "shipped",
        "DELIVERED": "delivered",
        "CANCELLED": "cancelled",
        "REFUNDED": "refunded"
    }
    
    # Status transitions that are allowed
    ALLOWED_STATUS_TRANSITIONS: Dict[str, List[str]] = {
        "pending": ["paid", "cancelled"],
        "paid": ["processing", "cancelled", "refunded"],
        "processing": ["shipped", "cancelled", "refunded"],
        "shipped": ["delivered", "refunded"],
        "delivered": ["refunded"],
        "cancelled": [],
        "refunded": []
    }
    
    # Validate URLs are properly formatted
    @validator("USER_SERVICE_URL", "PRODUCT_SERVICE_URL", "INVENTORY_SERVICE_URL", pre=True)
    def validate_service_urls(cls, v):
        if isinstance(v, str) and not v.startswith(("http://", "https://")):
            return f"http://{v}"
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings object
settings = Settings()