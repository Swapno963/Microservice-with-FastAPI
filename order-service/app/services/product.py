import httpx
import logging
from decimal import Decimal
from typing import Dict, List, Optional
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.config import settings

logger = logging.getLogger(__name__)


class ProductServiceClient:

    def __init__(self):
        self.base_url = str(settings.PRODUCT_SERVICE_URL)
        self.timeout = 5.0  # seconds
        self.max_retries = settings.MAX_RETRIES
        self.retry_delay = settings.RETRY_DELAY

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def verify_products(self, items: List) -> bool:
        """
        Verify that all products in an order exist and have valid prices.

        Args:
            items: List of OrderItem objects with product_id, quantity, and price

        Returns:
            bool: True if all products are valid, False otherwise
        """
        logger.info(f"Verifying {len(items)} products")

        for item in items:
            # Fix: Access attributes directly instead of using .get()
            product_id = item.product_id
            price = Decimal(str(item.price))

            product = await self.get_product(product_id)
            if not product:
                logger.warning(f"Product not found: {product_id}")
                return False

            # Verify the price matches (allow for small difference due to decimal precision)
            product_price = Decimal(str(product.get("price")))
            if abs(product_price - price) > Decimal("0.01"):
                logger.warning(
                    f"Price mismatch for product {product_id}: {price} vs {product_price}"
                )
                return False

        return True


product_service = ProductServiceClient()
