import httpx
import logging
from decimal import Decimal
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.config import settings

logger = logging.getLogger(__name__)


class InventoryServiceClient:
    """Client for interacting with the Inventory Service."""

    def __init__(self):
        self.base_url = str(settings.INVENTORY_SERVICE_URL)
        self.timeout = 5.0  # seconds
        self.max_retries = settings.MAX_RETRIES
        self.retry_delay = settings.RETRY_DELAY

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def check_inventory(self, product_id: str, quantity: int) -> bool:
        """
        Check if the specified quantity of a product is available.

        Args:
            product_id: The ID of the product
            quantity: The quantity to check

        Returns:
            bool: True if sufficient inventory exists, False otherwise
        """
        logger.info(f"Checking inventory for product {product_id}, quantity {quantity}")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/inventory/check",
                    params={"product_id": product_id, "quantity": quantity},
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get("available", False)
                else:
                    logger.error(f"Inventory check failed: {response.text}")
                    return False
        except httpx.RequestError as e:
            logger.error(f"Error checking inventory: {str(e)}")
            return False
