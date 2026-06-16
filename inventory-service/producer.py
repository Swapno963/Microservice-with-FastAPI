from fastapi import FastAPI
from aiokafka import AIOKafkaProducer
import json
import asyncio
from datetime import datetime

app = FastAPI()

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
TOPIC = "order-events"

producer = None


@app.on_event("startup")
async def startup():
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()


@app.on_event("shutdown")
async def shutdown():
    await producer.stop()


@app.post("/create-order")
async def create_order():
    event = {
        "event_name": "OrderCreated",
        "order_id": "ORD-123",
        "user_id": "U-1",
        "product_id": "P-1",
        "quantity": 2,
        "timestamp": datetime.utcnow().isoformat(),
    }

    await producer.send_and_wait(TOPIC, event)

    return {"message": "order created", "event_published": True}