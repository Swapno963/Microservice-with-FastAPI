from fastapi import FastAPI
from aiokafka import AIOKafkaConsumer
import json
import asyncio

app = FastAPI()

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
TOPIC = "order-events"

consumer = None


async def consume_events():
    global consumer

    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="inventory-service",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

    await consumer.start()

    try:
        async for message in consumer:
            event = message.value
            print("Received event:", event)

            if event["event_name"] == "OrderCreated":
                await reserve_inventory(event)

    finally:
        await consumer.stop()


async def reserve_inventory(event):
    print(f"Reserving inventory for product {event['product_id']}")
    # simulate DB update
    return True


@app.on_event("startup")
async def startup():
    asyncio.create_task(consume_events())