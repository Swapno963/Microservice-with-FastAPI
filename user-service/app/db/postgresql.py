import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.core.config import settings
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


# Configuring logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("user-service")


# Convert synchronous postgres URL to async
DATABASE_URL = str(settings.DATABASE_URL)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)


# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,  # Enable SQL query logging if in debug mode
    future=True,  # Use future mode for SQLAlchemy 2.0 compatibility
)


# Create async session factory
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Create base class for declarative models
Base = declarative_base()


async def initalize_db():
    """Initialize database with required tables."""
    async with engine.begin() as conn:
        # Create table if they don't exists
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initalized")


async def close_db_connection():
    """Close databse connection"""
    await engine.despose()
    logger.info("Database connection closed")


# Dependency for getting a databse session
async def get_db():
    """Dependency for getting an async databse session"""
    async with AsyncSessionLocal as session:
        try:
            yield session
        finally:
            await session.close()
