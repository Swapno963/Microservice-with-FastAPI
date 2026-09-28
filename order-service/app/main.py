from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import orders
from app.core.config import settings
from app.db.mongodb import close_mongo_connection, connect_to_mongo
from app.queue import close_redis, connect_redis

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Order Service API",
    version="1.0.0",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Set up API routes
app.include_router(orders.router, prefix=settings.API_PREFIX)

# Register startup and shutdown events
app.add_event_handler("startup", connect_to_mongo)
app.add_event_handler("startup", connect_redis)
app.add_event_handler("shutdown", close_redis)
app.add_event_handler("shutdown", close_mongo_connection)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "order-service"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=False)
