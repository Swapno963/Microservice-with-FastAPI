from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body, status
import logging


# Configure logger
logger = logging.getLogger(__name__)


# Create router
router = APIRouter(prefix="/orders", tags=["orders"])
