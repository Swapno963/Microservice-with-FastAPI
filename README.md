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




# User Microservice

A dedicated microservice for managing all user-related functionality. This service handles user authentication, profile management, and account security.

### Features

This microservice includes the following key functionalities:

* **Registration:** New user account creation.
* **Login:** User authentication to grant access.
* **Token Management:** Ability to get a new access token using a refresh token.
* **User Profile:** Retrieve and update user profile information.
* **Password Management:** Securely change user passwords.
* **Address Management:** Create and manage user addresses.
* **Account Verification:** Verify if a user account already exists.

![A screenshot of the User Microservice](project-screenshot/User%20Service.png)