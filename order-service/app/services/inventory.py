import httpx
import logging
from decimal import Decimal
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.config import settings

logger = logging.getLogger(__name__)


class InventoryCallError(Exception):
    """Inventory HTTP call failed. The worker decides whether to retry."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


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

    async def reserve_inventory(
        self,
        product_id: str,
        quantity: int,
        order_id: str,
        expires_at=None,
    ) -> dict:
        """
        Reserve inventory for one order line.

        Raises InventoryCallError when the call does not succeed. The worker
        owns retries, so this method does not retry on its own.
        """
        payload = {
            "product_id": product_id,
            "quantity": quantity,
            "order_id": order_id,
        }
        if expires_at is not None:
            payload["expires_at"] = (
                expires_at.isoformat()
                if hasattr(expires_at, "isoformat")
                else expires_at
            )

        logger.info(
            "Reserving inventory for product %s quantity %s order %s",
            product_id,
            quantity,
            order_id,
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/inventory/reserve",
                    headers={
                        "X-Service-Token": settings.INTERNAL_SERVICE_TOKEN,
                    },
                    json=payload,
                )
        except httpx.RequestError as exc:
            logger.error("Error reserving inventory: %s", exc)
            raise InventoryCallError(0, str(exc)) from exc

        if response.status_code == 200 and response.json().get("reserved"):
            return response.json()

        logger.error("Inventory reservation failed: %s", response.text)
        raise InventoryCallError(response.status_code, response.text)

    async def release_inventory(
        self, product_id: str, quantity: int, order_id: str
    ) -> dict:
        """Release a hold for one order line. Repeat calls are safe."""
        logger.info(
            "Releasing inventory for product %s quantity %s order %s",
            product_id,
            quantity,
            order_id,
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/inventory/release",
                    headers={
                        "X-Service-Token": settings.INTERNAL_SERVICE_TOKEN,
                    },
                    json={
                        "product_id": product_id,
                        "quantity": quantity,
                        "order_id": order_id,
                    },
                )
        except httpx.RequestError as exc:
            logger.error("Error releasing inventory: %s", exc)
            raise InventoryCallError(0, str(exc)) from exc

        if response.status_code == 200:
            return response.json()

        logger.error("Inventory release failed: %s", response.text)
        raise InventoryCallError(response.status_code, response.text)


inventory_service = InventoryServiceClient()
