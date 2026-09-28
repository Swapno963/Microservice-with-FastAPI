import json
from datetime import datetime, timedelta, timezone

import pytest

from app.queue import RESERVE_RETRY
from app.services.inventory import InventoryCallError
from app.worker.loops import handle_release, handle_reserve_job


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.zsets = {}

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return None
        self.values[key] = value
        return True

    async def delete(self, key):
        self.values.pop(key, None)
        return 1

    async def lpush(self, key, value):
        return 1

    async def zadd(self, key, mapping):
        self.zsets.setdefault(key, {}).update(mapping)
        return len(mapping)

    async def zrem(self, key, member):
        bucket = self.zsets.get(key, {})
        if member in bucket:
            del bucket[member]
            return 1
        return 0


class MemoryOrders:
    def __init__(self, order):
        self.order = order

    async def get_order(self, order_id):
        return self.order

    async def update_order(self, order_id, fields):
        self.order.update(fields)


class FakeInventory:
    def __init__(self, fail_product=None):
        self.fail_product = fail_product
        self.reserved = []
        self.released = []

    async def reserve_inventory(self, product_id, quantity, order_id, expires_at=None):
        if product_id == self.fail_product:
            raise InventoryCallError(503, "inventory down")
        self.reserved.append(product_id)

    async def release_inventory(self, product_id, quantity, order_id):
        self.released.append(product_id)


def _order(status="pending", state="pending", items=None):
    return {
        "status": status,
        "reservation_state": state,
        "reserve_attempts": 0,
        "reservation_expires_at": datetime.now(timezone.utc) + timedelta(minutes=15),
        "items": items
        or [
            {"product_id": "sku-a", "quantity": 1},
            {"product_id": "sku-b", "quantity": 1},
        ],
    }


@pytest.mark.asyncio
async def test_successful_reserve_marks_order_reserved():
    orders = MemoryOrders(_order(items=[{"product_id": "sku-a", "quantity": 1}]))
    inventory = FakeInventory()
    redis = FakeRedis()

    await handle_reserve_job(
        redis, orders, inventory, {"order_id": "ord-1", "attempt": 1}
    )

    assert orders.order["reservation_state"] == "reserved"
    assert orders.order["reserve_attempts"] == 1
    assert inventory.reserved == ["sku-a"]
    assert "ord-1" in redis.zsets.get("orders:release", {})


@pytest.mark.asyncio
async def test_down_inventory_retries_then_fails_and_releases_partial_hold():
    orders = MemoryOrders(_order())
    inventory = FakeInventory(fail_product="sku-b")
    redis = FakeRedis()

    await handle_reserve_job(
        redis, orders, inventory, {"order_id": "ord-1", "attempt": 1}
    )

    assert orders.order["reservation_state"] == "pending"
    assert inventory.released == ["sku-a"]
    retry_jobs = list(redis.zsets[RESERVE_RETRY])
    assert len(retry_jobs) == 1
    assert json.loads(retry_jobs[0])["attempt"] == 2

    await handle_reserve_job(
        redis, orders, inventory, {"order_id": "ord-1", "attempt": 5}
    )

    assert orders.order["reservation_state"] == "failed"
    assert inventory.released.count("sku-a") == 2
    assert len(redis.zsets[RESERVE_RETRY]) == 1


@pytest.mark.asyncio
async def test_due_expiry_releases_pending_order_and_leaves_paid_order():
    pending = MemoryOrders(
        _order(status="pending", state="reserved", items=[{"product_id": "sku-a", "quantity": 1}])
    )
    pending_inventory = FakeInventory()
    redis = FakeRedis()

    await handle_release(redis, pending, pending_inventory, "ord-pending")

    assert pending_inventory.released == ["sku-a"]
    assert pending.order["reservation_state"] == "released"

    paid = MemoryOrders(
        _order(status="paid", state="reserved", items=[{"product_id": "sku-a", "quantity": 1}])
    )
    paid_inventory = FakeInventory()

    await handle_release(redis, paid, paid_inventory, "ord-paid")

    assert paid_inventory.released == []
    assert paid.order["reservation_state"] == "reserved"
