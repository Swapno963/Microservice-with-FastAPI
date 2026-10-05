# Observability Architecture

## Goal

The goal of this project is not simply to "add monitoring".

The goal is to build a production-oriented observability system for an
EKS-based microservices application that allows us to answer three questions:

1. **What is happening?** → Metrics
2. **Why is it happening?** → Logs
3. **Where is the request spending time or failing?** → Distributed Tracing

The observability stack will combine:

- OpenTelemetry
- Prometheus
- Grafana
- Loki
- Tempo
- AWS CloudWatch

---

# 1. Architecture

```text
                         AWS / EKS
                            │
              ┌─────────────┴─────────────┐
              │                           │
        AWS Infrastructure          Microservices
              │                           │
              ↓                           ↓
         CloudWatch              OpenTelemetry SDK
              │                           │
              │                    OTel Collector
              │                           │
              │              ┌────────────┼────────────┐
              │              │            │            │
              │              ↓            ↓            ↓
              │         Prometheus       Loki         Tempo
              │              │            │            │
              │              └────────────┼────────────┘
              │                           │
              └───────────────────────────┤
                                          ↓
                                       Grafana
````

---

# 2. Why Two Monitoring Systems?

We intentionally use both AWS-native monitoring and
open-source observability.

They solve different problems.

```text
AWS CloudWatch
        │
        └── AWS infrastructure / platform visibility

OpenTelemetry
        │
        └── Application telemetry

Prometheus
        │
        └── Metrics

Loki
        │
        └── Logs

Tempo
        │
        └── Distributed traces

Grafana
        │
        └── Unified visualization
```

The objective is not to use as many tools as possible.

The objective is to understand which tool is appropriate for which
observability problem.

---

# 3. Responsibility Breakdown

## Task 1 — AWS CloudWatch

### Responsibility

Monitor the AWS/EKS infrastructure layer.

### What we monitor

* EKS infrastructure
* EC2/node metrics
* AWS Load Balancer metrics
* AWS service health/events
* Infrastructure-level logs where appropriate
* AWS alarms

### Why?

CloudWatch is AWS's native observability platform.

It gives us visibility into the infrastructure that Kubernetes itself
depends on.

For example:

```text
Application is slow
        │
        ├── Is the application slow?
        │       ↓
        │   Prometheus
        │
        └── Is the underlying AWS infrastructure unhealthy?
                ↓
            CloudWatch
```

### Production value

This demonstrates that we understand AWS-native operations rather than
only installing open-source monitoring tools.

---

# 4. Task 2 — OpenTelemetry

## Responsibility

Collect application telemetry in a vendor-neutral format.

OpenTelemetry will be the instrumentation and telemetry pipeline for
the microservices.

```text
FastAPI Service
      │
      ↓
OpenTelemetry instrumentation
      │
      ↓
OTel Collector
```

### Telemetry types

OpenTelemetry will handle:

* Traces
* Metrics
* Logs where appropriate

### Why?

Without instrumentation, we mostly know that something is wrong.

With OpenTelemetry, the application can tell us:

```text
Request started
       ↓
Database query
       ↓
HTTP call to another service
       ↓
Another service
       ↓
Response
```

This is particularly important for a microservices architecture.

---

# 5. Task 3 — Prometheus

## Responsibility

Store and query metrics.

Examples:

```text
HTTP request count
HTTP request rate
HTTP 4xx/5xx
Request latency
CPU usage
Memory usage
Pod restarts
Container resource usage
```

### Example question

> How many 5xx responses is order-service producing?

Prometheus should answer that.

### Why?

Metrics are excellent for detecting trends and defining alerts.

Example:

```text
HTTP 5xx rate
     │
     │        /
     │       /
     │      /
     │_____/
           ↑
        incident
```

Prometheus helps us detect this before users start reporting the
problem.

---

# 6. Task 4 — Loki

## Responsibility

Centralized application/container logs.

Instead of logging into individual Kubernetes Pods:

```text
kubectl logs pod-1
kubectl logs pod-2
kubectl logs pod-3
```

we centralize logs.

```text
Pod
 │
 └── logs
       ↓
      Loki
       ↓
    Grafana
```

### Why?

Pods are temporary.

A Pod can disappear because of:

* Deployment
* CrashLoopBackOff
* Rescheduling
* Node failure
* Scaling

Therefore, application logs should not depend on the lifetime of an
individual Pod.

### Example

Search:

```text
service = order-service
level = ERROR
```

and investigate application failures centrally.

---

# 7. Task 5 — Tempo

## Responsibility

Distributed tracing.

Tempo stores distributed traces generated by OpenTelemetry.

```text
OpenTelemetry
      │
      ↓
    Tempo
      │
      ↓
   Grafana
```

### Why?

Logs tell us:

> Something failed.

Metrics tell us:

> Failures increased.

Traces tell us:

> Which service caused the failure and where the request spent its time.

This is especially valuable in microservices.

---

# 8. KILLER FEATURE — End-to-End Distributed Tracing

This is the most important observability feature in the project.

The goal is to demonstrate a real request flowing through multiple
microservices.

For example:

```text
POST /api/v1/orders
        │
        ↓
   order-service
        │
        ├──────────────→ user-service
        │
        ├──────────────→ product-service
        │
        ├──────────────→ inventory-service
        │
        └──────────────→ database
```

OpenTelemetry generates a single trace:

```text
Trace ID: abc123

order-service
│
├── user-service
│     └── PostgreSQL
│
├── product-service
│     └── MongoDB
│
├── inventory-service
│     └── PostgreSQL
│
└── response
```

---

# 9. Killer Feature — Failure Investigation

We should intentionally demonstrate a failure scenario.

For example:

```text
User creates order
        │
        ↓
order-service
        │
        ↓
product-service
        │
        ↓
MongoDB
        │
        X
    slow/failure
```

Grafana should allow us to move from:

```text
High request latency
        ↓
Trace
        ↓
product-service is slow
        ↓
Database operation is slow
        ↓
Loki logs
        ↓
Database-related error
```

This demonstrates actual observability rather than just dashboards.

---

# 10. Grafana

## Responsibility

Grafana is the visualization and investigation layer.

Grafana will connect to:

```text
Prometheus → Metrics
Loki       → Logs
Tempo      → Traces
```

Potential dashboards:

### Application Dashboard

```text
Request Rate
Error Rate
Latency
Active Requests
```

### Kubernetes Dashboard

```text
Pod CPU
Pod Memory
Pod Restarts
Deployment Availability
Node Resource Usage
```

### Service Dashboard

```text
order-service
product-service
inventory-service
user-service
```

### Database Dashboard

```text
PostgreSQL
MongoDB
```

---

# 11. Grafana Correlation

One of the most important goals is to connect:

```text
Metrics
   ↓
Traces
   ↓
Logs
```

Example:

```text
Grafana
│
├── HTTP latency increased
│
├── Open trace
│      ↓
│   order-service
│      ↓
│   product-service
│      ↓
│   MongoDB
│
└── Open related logs
       ↓
    MongoDB connection timeout
```

This creates a complete troubleshooting workflow.

---

# 12. Alerts

Monitoring without alerting is incomplete.

We should create alerts for important operational conditions.

## Application

* High HTTP 5xx rate
* High request latency
* Service unavailable

## Kubernetes

* Pod CrashLoopBackOff
* Pod restart increase
* Deployment unavailable
* Node resource exhaustion

## Infrastructure

* High CPU
* High memory
* Disk pressure

## Database

* High connection usage
* Database unavailable
* Resource exhaustion

Alerts should be actionable.

Avoid creating alerts for every metric.

---

# 13. Implementation Tasks

The implementation should be done in this order.

## Phase 1 — AWS Monitoring

* Configure CloudWatch visibility
* Monitor EKS/node infrastructure
* Monitor Load Balancer
* Configure relevant AWS alarms

### Result

AWS infrastructure becomes observable.

---

## Phase 2 — Application Instrumentation

Add OpenTelemetry instrumentation to:

* user-service
* product-service
* inventory-service
* order-service

Capture:

* HTTP requests
* HTTP response status
* request duration
* service-to-service calls
* database operations where supported

### Result

Applications produce telemetry.

---

## Phase 3 — OpenTelemetry Collector

Deploy the OpenTelemetry Collector inside EKS.

```text
Microservices
      ↓
OTel Collector
```

Configure exporters:

```text
Traces  → Tempo
Metrics → Prometheus
Logs    → Loki
```

### Result

Telemetry is collected centrally.

---

## Phase 4 — Prometheus

Deploy/configure Prometheus.

Collect:

* Kubernetes metrics
* Application metrics
* Service metrics

Create recording rules where useful.

### Result

We can monitor application and Kubernetes behavior quantitatively.

---

## Phase 5 — Loki

Deploy Loki and configure log collection.

Collect:

* Application logs
* Container logs
* Kubernetes workload logs

### Result

Logs survive Pod lifecycle changes and can be searched centrally.

---

## Phase 6 — Tempo

Deploy Tempo.

Configure OpenTelemetry to send traces to Tempo.

### Result

Distributed traces become available.

---

## Phase 7 — Grafana

Connect:

```text
Prometheus
Loki
Tempo
```

Create dashboards for:

* Application
* Kubernetes
* Services
* Infrastructure
* Database

---

## Phase 8 — Observability Correlation

Configure Grafana so that:

```text
Metric
  ↓
Trace
  ↓
Logs
```

can be followed during troubleshooting.

This is a key production-oriented feature.

---

# 14. Final Architecture

```text
                         USERS
                           │
                           ↓
                    AWS Load Balancer
                           │
                           ↓
                         EKS
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ↓                ↓                ↓
   user-service      product-service   order-service
          │                │                │
          └────────────────┼────────────────┘
                           │
                    OpenTelemetry
                           │
                    OTel Collector
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ↓                ↓                ↓
     Prometheus          Loki             Tempo
       Metrics           Logs             Traces
          │                │                │
          └────────────────┼────────────────┘
                           ↓
                        Grafana
                           │
                           │
AWS Infrastructure ─────→ CloudWatch
```

---

# 15. Why This Architecture?

Each component has a specific responsibility.

| Tool          | Responsibility                  | Main Question                                   |
| ------------- | ------------------------------- | ----------------------------------------------- |
| CloudWatch    | AWS infrastructure              | Is AWS/EKS infrastructure healthy?              |
| OpenTelemetry | Telemetry generation/collection | What is happening inside the application?       |
| Prometheus    | Metrics                         | What is the system doing over time?             |
| Loki          | Logs                            | What happened?                                  |
| Tempo         | Traces                          | Where did the request go and where was it slow? |
| Grafana       | Visualization/correlation       | How do we investigate the incident?             |

The architecture avoids using one tool for everything.

---

# 16. Beginner vs Experienced vs Production Approach

## Beginner

```text
CloudWatch
+
Basic Grafana dashboard
```

Good for learning basic monitoring.

---

## Experienced

```text
Prometheus
Loki
Grafana
OpenTelemetry
Tempo
```

Provides complete application observability.

---

## Production-oriented

```text
AWS CloudWatch
        +
OpenTelemetry
        +
Prometheus
        +
Loki
        +
Tempo
        +
Grafana
        +
Alerting
        +
Metric/trace/log correlation
```

This is the target architecture for this project.

The objective is not to claim that this is the only correct production
architecture.

The objective is to demonstrate the ability to design an observability
system based on operational requirements.

---

# 17. Portfolio / Resume Value

The final project should demonstrate:

### Infrastructure

* AWS
* EKS
* Kubernetes
* Docker

### Observability

* OpenTelemetry
* Prometheus
* Grafana
* Loki
* Tempo
* CloudWatch

### Engineering Skills

* Distributed tracing
* Centralized logging
* Metrics
* Alerting
* Failure investigation
* Kubernetes troubleshooting
* Service-to-service observability

---

# 18. Resume-Level Outcome

The strongest part of this implementation should be the ability to
demonstrate:

> A request enters the system, travels across multiple microservices,
> generates a distributed trace, produces correlated metrics and logs,
> and can be investigated from a single Grafana interface.

That is the "killer feature" of the observability implementation.

It demonstrates that the project is not simply:

> "I deployed some microservices on EKS."

Instead, it demonstrates:

> "I can operate and troubleshoot a distributed application."

---

# 19. Definition of Done

The observability implementation is complete when we can demonstrate:

* [ ] AWS/EKS infrastructure visible in CloudWatch
* [ ] Kubernetes metrics available
* [ ] Application metrics available
* [ ] Centralized application logs available
* [ ] Distributed traces available
* [ ] Grafana connected to Prometheus
* [ ] Grafana connected to Loki
* [ ] Grafana connected to Tempo
* [ ] Alerts configured for important failures
* [ ] Metrics → traces correlation works
* [ ] Traces → logs correlation works
* [ ] At least one complete request spans multiple services
* [ ] A deliberate failure can be investigated end-to-end

## Final Demonstration

The final demo should show:

```text
1. Create an order
        ↓
2. Find the request metric
        ↓
3. Open the distributed trace
        ↓
4. Follow order-service
        ↓
5. Follow product-service
        ↓
6. Follow inventory-service
        ↓
7. Inspect database operation
        ↓
8. Open correlated logs
        ↓
9. Identify the failure/latency
        ↓
10. Fix the underlying issue
```

This is the core demonstration of the project's observability capability.

```
