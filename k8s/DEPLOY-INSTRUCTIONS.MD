## Build and push the Service images

docker build -t swapno/user-service:latest ./user-service
docker push swapno/user-service:latest


docker build -t swapno/product-service:latest ./product-service
docker push swapno/product-service:latest



docker build -t swapno/order-service:latest ./order-service
docker push swapno/order-service:latest


docker build -t swapno/inventory-service:latest ./inventory-service
docker push swapno/inventory-service:latest


kubectl apply -f k8s/postgres-user.yaml
kubectl apply -f k8s/postgres-inventory.yaml
kubectl apply -f k8s/mongodb-product.yaml
kubectl apply -f k8s/mongodb-order.yaml




Deploy All Application Services
kubectl apply -f k8s/user-service.yaml
kubectl apply -f k8s/product-service.yaml
kubectl apply -f k8s/order-service.yaml
kubectl apply -f k8s/inventory-service.yaml


Deploy the Nginx Gateway
kubectl apply -f k8s/nginx-configmap.yaml
kubectl apply -f k8s/nginx-gateway.yaml

Build and deploy the React frontend. The image serves the built app and proxies /api to the services above.

docker build -f frontend/Dockerfile -t swapno/shopverse-frontend:latest .
docker push swapno/shopverse-frontend:latest
kubectl apply -f k8s/frontend.yaml
