from app.core.config import settings
import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


class UserService:

    def __init__(self):
        self.base_url = str(settings.USER_SERVICE_URL)
        self.timeout = 5.0  # seconds
        self.max_retries = settings.MAX_RETRIES
        self.retry_delay = settings.RETRY_DELAY

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def verify_user(self, user_id: str) -> bool:
        """
        Verify that a user exists and is active.

        Args:
            user_id: The ID of the user to check

        Returns:
            bool: True if user exists and is active, False otherwise
        """
        logger.info("Verifying user: %s", user_id)
        if not user_id.isdigit():
            logger.warning("Rejected non-numeric user id: %s", user_id)
            return False
        try:
            url = f"{self.base_url}/users/{int(user_id)}/verify"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers={
                        "X-Service-Token": settings.INTERNAL_SERVICE_TOKEN,
                    },
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get("valid", False)
                logger.warning(
                    "User verification failed with status %s",
                    response.status_code,
                )
                return False
        except httpx.RequestError as e:
            logger.error("Error verifying user: %s", e)
            return False


user_service = UserService()
