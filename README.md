# FastAPI commerce microservices

Lab: four independently deployable services for a small e-commerce domain. Built to practice service boundaries and inventory correctness, not to run a live store.

**Status:** lab. No production traffic. Frontend/Next.js is not in this repo. Payment service is not built.

---

## What it does

| Service | Database | Job |
| --- | --- | --- |
| User | MongoDB (see service code; some docs mentioned Postgres) | Register, login, refresh tokens, profile, addresses |
| Product | MongoDB | Catalog and categories |
| Inventory | PostgreSQL | Stock, reserve/release/adjust inside transactions |
| Order | MongoDB | Create pending orders after inventory reserve; cancel releases stock |

Inventory is the scarce resource. PostgreSQL with row-level locking (`SELECT ... FOR UPDATE`) and transactional history is used so oversell is harder. Other services store documents in MongoDB. Calls between services are synchronous HTTP today.

If reserve fails, the order stays pending and the client can retry. Saga / outbox compensation is **not shipped**.

---

## What I built

- FastAPI services with their own Dockerfiles (multi-stage) and compose files
- Inventory reserve/release/adjust under transactions
- Order create/cancel that talks to inventory
- Low-stock listing on inventory

---

## Stack

Python, FastAPI, PostgreSQL, MongoDB, Docker Compose. Nginx folder exists for routing experiments.

---

## Run

```bash
git clone https://github.com/Swapno963/Microservice-with-FastAPI.git
cd Microservice-with-FastAPI
docker compose up --build
```

Optional base image: `docker build -t fastapi-base:1.0 -f Dockerfile.base .`

Architecture diagram: `project-screenshot/E-commerce Arch.svg`
