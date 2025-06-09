from pydantic import validator, PostgresDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Api settings
    API_PREFIX: str = "/api/v1"  # Route prefix for all API routes
    DEBUG: bool = False
    PROJECT_NAME: str = "User Service"
    PORT: int = 8003

    # Database settings
    DATABASE_URL: PostgresDsn

    # Jwt settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Security
    SECURITY_PASSWORD_SALT: str
    SECURITY_PASSWORD_HASH: str = "bcrypt"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings object
settings = Settings()
