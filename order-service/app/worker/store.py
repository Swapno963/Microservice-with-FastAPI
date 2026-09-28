from datetime import datetime

from bson import ObjectId


class MongoOrders:
    """Order reads and writes used by the worker."""

    def __init__(self, db):
        self.db = db

    async def get_order(self, order_id: str):
        if not ObjectId.is_valid(order_id):
            return None
        return await self.db["orders"].find_one({"_id": ObjectId(order_id)})

    async def update_order(self, order_id: str, fields: dict) -> None:
        fields = dict(fields)
        fields["updated_at"] = datetime.utcnow()
        await self.db["orders"].update_one(
            {"_id": ObjectId(order_id)},
            {"$set": fields},
        )
