import os
from typing import Optional
from pydantic import BaseSettings, validator, AnyHttpUrl


class Settings(BaseSettings):
    # API settings
    API_PREFIX: str = "/api/v1/products"
    DEBUG: bool = False
    PROJECT_NAME: str = "Product Service"
    CORS_ORIGIN: str = "http://localhost:8080"

    # MongoDB settings
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "product_db"

    # Service URLs
    INVENTORY_SERVICE_URL: Optional[AnyHttpUrl] = None

    # Authentication shared with the user service.
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    INTERNAL_SERVICE_TOKEN: str

    # Validate URLs are properly formatted
    @validator("INVENTORY_SERVICE_URL", pre=True)
    def validate_service_urls(cls, v):
        if isinstance(v, str) and not v.startswith(("http://", "https://")):
            return f"http://{v}"
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings object
settings = Settings()
