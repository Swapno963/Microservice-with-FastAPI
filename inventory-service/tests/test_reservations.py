import asyncio
import os
import tempfile

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes.inventory import release_inventory, reserve_inventory
from app.db.postgresql import Base
from app.models.inventory import InventoryItem, InventoryRelease, InventoryReserve

USER = {"sub": "tester", "is_admin": True}


@pytest.fixture
async def session_factory(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.inventory.settings.ENABLE_NOTIFICATIONS", False
    )
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()
    os.remove(path)


async def _seed(factory, available=1):
    async with factory() as session:
        session.add(
            InventoryItem(
                product_id="sku-1",
                available_quantity=available,
                reserved_quantity=0,
                reorder_threshold=0,
            )
        )
        await session.commit()


async def test_concurrent_reserves_of_last_unit(session_factory):
    await _seed(session_factory, available=1)

    async def attempt(order_id):
        async with session_factory() as session:
            return await reserve_inventory(
                InventoryReserve(product_id="sku-1", quantity=1, order_id=order_id),
                session,
                USER,
            )

    results = await asyncio.gather(
        attempt("order-a"),
        attempt("order-b"),
        return_exceptions=True,
    )
    successes = [result for result in results if isinstance(result, dict)]
    failures = [result for result in results if isinstance(result, HTTPException)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert failures[0].status_code == 400

    async with session_factory() as session:
        item = await session.get(InventoryItem, 1)
        assert item.available_quantity == 0
        assert item.reserved_quantity == 1


async def test_repeat_reserve_does_not_double_decrement(session_factory):
    await _seed(session_factory, available=5)

    async with session_factory() as session:
        first = await reserve_inventory(
            InventoryReserve(product_id="sku-1", quantity=2, order_id="order-1"),
            session,
            USER,
        )
        second = await reserve_inventory(
            InventoryReserve(product_id="sku-1", quantity=2, order_id="order-1"),
            session,
            USER,
        )

    assert first["reserved"] is True
    assert second["idempotent"] is True
    assert second["available_quantity"] == 3
    assert second["reserved_quantity"] == 2


async def test_repeat_release_is_a_noop(session_factory):
    await _seed(session_factory, available=5)

    async with session_factory() as session:
        await reserve_inventory(
            InventoryReserve(product_id="sku-1", quantity=2, order_id="order-1"),
            session,
            USER,
        )
        released = await release_inventory(
            InventoryRelease(product_id="sku-1", quantity=2, order_id="order-1"),
            session,
            USER,
        )
        again = await release_inventory(
            InventoryRelease(product_id="sku-1", quantity=2, order_id="order-1"),
            session,
            USER,
        )
        item = await session.get(InventoryItem, 1)

    assert released["released"] is True
    assert again["already_released"] is True
    assert item.available_quantity == 5
    assert item.reserved_quantity == 0
