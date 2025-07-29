# 🧩 Microservice Application

This is a full-stack microservice-based application built using:

- **Frontend**: React.js / Next.js(Pending)
- **Backend**: FastAPI (Ongoing)
- **Databases**: PostgreSQL and MongoDB
- **Containerization**: Docker (multi-stage Dockerfiles)

## 🧱 Project Structure
- **User Service**: Handles authentication, registration, and user management.
- **Inventory Service**: Manages stock levels, warehouses, and inventory operations.
- **Product Service**: Maintains product data, categories, and pricing.
- *(Upcoming)* **Payment Service**: Will manage transactions, payment gateways, and order settlements.

Each microservice is containerized using a **multi-stage Dockerfile** for optimized production builds.

## 🚀 Features

- Authentication and Authorization
- RESTful APIs (FastAPI, Django REST Framework)
- PostgreSQL and MongoDB as backend databases
- Modern frontend with React.js and Next.js
- Dockerized with multi-stage builds
- Scalable and modular microservice architecture

## 🐳 Docker Setup

### Prerequisites

- Docker
- Docker Compose

### Running the app

```bash
# Clone the repo
git clone https://github.com/Swapno963/Microservice-with-FastAPI.git
cd Microservice-with-FastAPI

# Build and start all services
docker-compose up --build
```


