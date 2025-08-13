from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import orders
from app.core.config import settings
from app.db.mongodb import close_mongo_connection, connect_to_mongo

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
    allow_origins=["*"],  # For production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "order-service"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
