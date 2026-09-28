import asyncio
import json
import logging
import time
from datetime import datetime, timezone

from app.core.config import settings
from app.queue import (
    RELEASE_QUEUE,
    RESERVE_QUEUE,
    RESERVE_RETRY,
    enqueue_release,
    enqueue_reserve_retry,
    lock_key,
)
from app.services.inventory import InventoryCallError

logger = logging.getLogger(__name__)

PAID_OR_LATER = {"paid", "processing", "shipped", "delivered", "refunded"}


def utc_timestamp(value) -> float:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.timestamp()
    return float(value)


async def promote_due_retries(redis, now: float = None) -> None:
    now = time.time() if now is None else now
    due = await redis.zrangebyscore(RESERVE_RETRY, "-inf", now)
    for member in due:
        removed = await redis.zrem(RESERVE_RETRY, member)
        if removed:
            await redis.lpush(RESERVE_QUEUE, member)


async def _acquire_lock(redis, order_id: str) -> bool:
    acquired = await redis.set(lock_key(order_id), "1", nx=True, ex=60)
    return bool(acquired)


async def _release_lock(redis, order_id: str) -> None:
    await redis.delete(lock_key(order_id))


async def _release_items(inventory, order_id: str, items) -> None:
    for item in items:
        await inventory.release_inventory(
            item["product_id"], item["quantity"], order_id
        )


async def handle_reserve_job(redis, orders, inventory, job: dict) -> None:
    order_id = job["order_id"]
    attempt = int(job.get("attempt", 1))

    if not await _acquire_lock(redis, order_id):
        await enqueue_reserve_retry(redis, order_id, attempt, time.time() + 1)
        return

    try:
        order = await orders.get_order(order_id)
        if not order:
            logger.warning("Reserve job for missing order %s", order_id)
            return

        status = order.get("status")
        state = order.get("reservation_state")
        if status != "pending" or state != "pending":
            if status == "cancelled" and state == "pending":
                try:
                    await _release_items(inventory, order_id, order.get("items", []))
                except InventoryCallError:
                    logger.exception("Release after cancel failed for %s", order_id)
                    await enqueue_release(redis, order_id, time.time() + 2)
                    return
                await orders.update_order(
                    order_id, {"reservation_state": "released"}
                )
            return

        held = []
        try:
            for item in order.get("items", []):
                await inventory.reserve_inventory(
                    item["product_id"],
                    item["quantity"],
                    order_id,
                    order.get("reservation_expires_at"),
                )
                held.append(item)
        except InventoryCallError:
            logger.warning(
                "Reserve attempt %s failed for order %s", attempt, order_id
            )
            for item in held:
                try:
                    await inventory.release_inventory(
                        item["product_id"], item["quantity"], order_id
                    )
                except InventoryCallError:
                    logger.exception(
                        "Could not release partial hold for order %s", order_id
                    )
            await _schedule_retry_or_fail(redis, orders, order_id, attempt)
            return

        order = await orders.get_order(order_id)
        if order.get("status") != "pending":
            try:
                await _release_items(inventory, order_id, order.get("items", []))
            except InventoryCallError:
                logger.exception("Release after status change failed for %s", order_id)
                await enqueue_release(redis, order_id, time.time() + 2)
                return
            await orders.update_order(order_id, {"reservation_state": "released"})
            return

        expires_at = order.get("reservation_expires_at")
        when = utc_timestamp(expires_at) if expires_at is not None else time.time()
        await enqueue_release(redis, order_id, when)
        await orders.update_order(
            order_id,
            {"reservation_state": "reserved", "reserve_attempts": attempt},
        )
        # Cancel can land after the read above and enqueue an immediate release
        # that this expiry score would overwrite. Put the immediate release back.
        order = await orders.get_order(order_id)
        if order.get("status") != "pending":
            await enqueue_release(redis, order_id, time.time())
        logger.info("Reserved inventory for order %s", order_id)
    finally:
        await _release_lock(redis, order_id)


async def _schedule_retry_or_fail(redis, orders, order_id: str, attempt: int) -> None:
    if attempt >= settings.MAX_RESERVE_ATTEMPTS:
        await orders.update_order(
            order_id,
            {"reservation_state": "failed", "reserve_attempts": attempt},
        )
        logger.info("Reservation failed for order %s after %s attempts", order_id, attempt)
        return

    await orders.update_order(order_id, {"reserve_attempts": attempt})
    backoff = settings.RESERVE_BACKOFF_SECONDS
    delay = backoff[min(attempt - 1, len(backoff) - 1)]
    await enqueue_reserve_retry(redis, order_id, attempt + 1, time.time() + delay)


async def handle_release(redis, orders, inventory, order_id: str) -> None:
    if not await _acquire_lock(redis, order_id):
        await enqueue_release(redis, order_id, time.time() + 2)
        return

    try:
        order = await orders.get_order(order_id)
        if not order:
            return

        status = order.get("status")
        state = order.get("reservation_state")

        if status in PAID_OR_LATER:
            logger.info("Leaving hold in place for %s order %s", status, order_id)
            return

        if state == "released":
            return

        if status == "pending" and state == "pending":
            return

        try:
            await _release_items(inventory, order_id, order.get("items", []))
        except InventoryCallError:
            logger.exception("Release failed for order %s", order_id)
            await enqueue_release(redis, order_id, time.time() + 5)
            return

        await orders.update_order(order_id, {"reservation_state": "released"})
        logger.info("Released inventory for order %s", order_id)
    finally:
        await _release_lock(redis, order_id)


async def reserve_loop(redis, orders, inventory) -> None:
    while True:
        await promote_due_retries(redis)
        popped = await redis.brpop(RESERVE_QUEUE, timeout=1)
        if not popped:
            continue
        _, raw = popped
        try:
            job = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("Dropping invalid reserve job: %s", raw)
            continue
        await handle_reserve_job(redis, orders, inventory, job)


async def release_loop(redis, orders, inventory) -> None:
    while True:
        now = time.time()
        due = await redis.zrangebyscore(RELEASE_QUEUE, "-inf", now)
        if not due:
            await asyncio.sleep(0.5)
            continue
        for order_id in due:
            removed = await redis.zrem(RELEASE_QUEUE, order_id)
            if removed:
                await handle_release(redis, orders, inventory, order_id)
