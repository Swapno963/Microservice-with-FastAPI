# FastAPI commerce microservices

Lab: four independently deployable services for a small e-commerce domain. Built to practice service boundaries and inventory correctness, not to run a live store.

**Status:** launch-oriented local MVP. No production traffic. Payment is not
built, so customers can reserve stock but cannot pay in this application.

---

## What it does

| Service | Database | Job |
| --- | --- | --- |
| User | MongoDB (see service code; some docs mentioned Postgres) | Register, login, refresh tokens, profile, addresses |
| Product | MongoDB | Catalog and categories |
| Inventory | PostgreSQL | Stock, reserve/release/adjust inside transactions |
| Order | MongoDB | Create a pending order and enqueue reservation. A worker reserves stock, retries failures, and releases expired or cancelled holds |

The Nginx gateway serves a small responsive shopper client. Customers can
register, sign in, browse products, reserve an item, view reservation state,
and cancel their own order.

Inventory is the scarce resource. PostgreSQL locks the stock row (`SELECT ... FOR UPDATE`) and writes an `inventory_reservations` row in the same transaction. Reserving the same order and product again does not decrement twice. Other services store documents in MongoDB.

Order create does not call inventory. It returns `202` and pushes a job onto Redis. `order-worker` reserves each line, retries with backoff, and releases partial holds when a try fails. After the attempt limit the order is marked `reservation_state=failed`. Cancel enqueues a release instead of calling inventory in the request. A due hold is released while the order is still pending. Paid and later orders keep their hold.

---

## What I built

- FastAPI services with their own Dockerfiles and compose files
- Inventory reserve/release/adjust under transactions, with idempotent reservation rows
- Order create returns pending immediately; `order-worker` retries reserve and releases stock via Redis
- Low-stock listing on inventory

---

## Stack

Python, FastAPI, PostgreSQL, MongoDB, Redis, Docker Compose. Nginx folder exists for routing experiments.

---

## Run

```bash
git clone https://github.com/Swapno963/Microservice-with-FastAPI.git
cd Microservice-with-FastAPI
cp .env.example .env
# Replace every value in .env with a unique random secret.
docker compose up --build
```

Open `http://localhost:8080`. The gateway is intentionally bound to localhost.
Keep it off the public internet until real TLS is configured in front of it.

New accounts are shoppers. To promote the first trusted merchant account after
registration:

```bash
docker compose exec postgres-user psql -U postgres -d user_db \
  -c "UPDATE users SET is_admin = TRUE WHERE email = 'merchant@example.com';"
```

Sign in again after promotion so the JWT contains the admin claim. Admin JWTs
can create products and adjust inventory. Customer JWTs can only read and
cancel their own orders. `POST /orders` requires an `Idempotency-Key` header.

Architecture diagram: `project-screenshot/E-commerce Arch.svg`
