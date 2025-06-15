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

### Relational Databases (SQL)
Examples: PostgreSQL, MySQL, MariaDB
1. Data is Structured with Clear Relationships
Relational databases use tables, and each table has columns and rows. When your data has a predictable schema (e.g., users, orders, products) and clear relationships (like one-to-many, many-to-many), relational databases are the best fit.

These tables are clearly connected: one user → many orders, one order → many items, etc.



2. You Need ACID Transactions
Explanation:
ACID stands for:

Atomicity: All parts of a transaction succeed or fail together.
Consistency: Data remains valid after any transaction.
Isolation: Transactions don’t interfere with each other.
Durability: Data is saved permanently once a transaction is committed.

Using an ACID-compliant database like PostgreSQL ensures that either both happen or neither happens — you won't lose or create money accidentally.



3. You Want Strong Data Consistency
Explanation:
Relational databases ensure that once data is written, reads will reflect the latest write. There’s no “eventual consistency” like in some NoSQL databases.

What is Eventual Consistency (NoSQL)?
Many NoSQL databases (like MongoDB, DynamoDB, Cassandra, Couchbase) use eventual consistency — especially in distributed setups.

🧠 It means: After a write, it may take time for all nodes (or replicas) to reflect the new value.

During that time, some reads might return old data.

🔍 Example: Eventual Consistency in NoSQL (MongoDB Replica Set or Cassandra)
Assume you have:

A MongoDB cluster with 1 primary and 2 secondary nodes.

Writes go to the primary.

Reads can happen from secondaries (depending on config).




4. Complex Queries or Joins Are Common
Explanation:
SQL in relational databases supports powerful queries, including joins, filtering, grouping, aggregations, subqueries, etc.

Real-World Example:
A university system:

To get a list of all students enrolled in a particular course along with their grades and professor names, you might join:

Students
Courses
Enrollments
Professors


❌ Avoid When:
Your schema changes frequently.
You need to scale writes horizontally without sharding.
You want to handle a lot of write operations (inserts/updates/deletes) by simply adding more machines (horizontally), and you don't want the complexity of manually splitting data across them (sharding).

NoSQL solutions like Cassandra or MongoDB:
Let you distribute writes across many nodes automatically
Handle horizontal scaling better out of the box



### 2. Document Databases (NoSQL)
Examples: MongoDB, Couchbase

✅ Use When:
You have semi-structured or unstructured data (e.g., nested JSON).

Schema changes frequently.

You need fast reads/writes and can tolerate eventual consistency.

❌ Avoid When:
You require complex joins or transactions across collections.





4. Wide-Column Stores
Examples: Apache Cassandra, HBase

✅ Use When:
You have high write throughput.

You need to scale horizontally and handle massive amounts of data.

You can design queries in advance (query-based modeling).

❌ Avoid When:
Your access patterns are unpredictable.

You need relational integrity.


3. Key-Value Stores
Examples: Redis, DynamoDB

✅ Use When:
You need super-fast reads/writes.

Data access is simple (key → value).

Used for caching, sessions, or simple data retrieval.

❌ Avoid When:
You need complex querying or data relationships.




5. Graph Databases
Examples: Neo4j, ArangoDB

✅ Use When:
You need to model and query complex relationships.

Relationship traversal is central to your queries (e.g., social networks).

❌ Avoid When:
You don’t have complex relationships to model.





6. Search Engines (Search Databases)
Examples: Elasticsearch, MeiliSearch

✅ Use When:
You need full-text search, filtering, and ranking.

You want fast and complex search capabilities.

❌ Avoid When:
You need transactional updates or strict consistency.

