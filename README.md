# 🧩 Microservice Application

This is a full-stack microservice-based application built using:

- **Frontend**: Next.js
- **Backend**: FastAPI
- **Databases**: PostgreSQL and MongoDB
- **Containerization**: Docker (multi-stage Dockerfiles)

## 🧱 Project Structure


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

### Mongo db: We use mongodb if data is nested
### Postgress: We use it if data is lenier
