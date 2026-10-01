kubectl apply -f k8s/postgres-user.yaml
kubectl apply -f k8s/postgres-inventory.yaml
kubectl apply -f k8s/mongodb-product.yaml
kubectl apply -f k8s/mongodb-order.yaml




Deploy All Application Services
kubectl apply -f k8s/user-service.yaml
kubectl apply -f k8s/product-service.yaml
kubectl apply -f k8s/order-service.yaml
kubectl apply -f k8s/inventory-service.yaml
