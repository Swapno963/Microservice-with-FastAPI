import asyncio
import logging

from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_database
from app.queue import close_redis, connect_redis, get_redis
from app.services.inventory import inventory_service
from app.worker.loops import release_loop, reserve_loop
from app.worker.store import MongoOrders

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    await connect_to_mongo()
    await connect_redis()
    redis = get_redis()
    orders = MongoOrders(get_database())
    try:
        logger.info("Order worker started")
        await asyncio.gather(
            reserve_loop(redis, orders, inventory_service),
            release_loop(redis, orders, inventory_service),
        )
    finally:
        await close_redis()
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
