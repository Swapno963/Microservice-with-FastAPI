Restaurant SaaS
→ Prometheus + Grafana + Loki + Alloy + Alertmanager

E-commerce EKS
→ OpenTelemetry + Tempo + Loki + Prometheus/Grafana
→ AWS CloudWatch for AWS/EKS infrastructure


Implemented distributed observability for an EKS microservices platform using OpenTelemetry, Prometheus, Grafana, Loki and Tempo, enabling metrics, centralized logging and distributed request tracing across services.


Very strong

If you can actually demonstrate:

HTTP request
   ↓
Trace ID
   ↓
order-service
   ↓
product-service
   ↓
inventory-service
   ↓
database


For your project, the killer feature is actually tracing a request across multiple FastAPI services.