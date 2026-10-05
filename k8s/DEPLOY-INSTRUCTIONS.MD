## Build and push the Service images

docker build -t swapno/user-service:latest ./user-service
docker push swapno/user-service:latest


docker build -t swapno/product-service:latest ./product-service
docker push swapno/product-service:latest



docker build -t swapno/order-service:latest ./order-service
docker push swapno/order-service:latest


docker build -t swapno/inventory-service:latest ./inventory-service
docker push swapno/inventory-service:latest


docker build -t swapno/frontend:latest -f frontend/Dockerfile .
docker push swapno/frontend:latest



## Create a new EKS cluster without a node group:
eksctl create cluster \
  --name todo-cluster \
  --version 1.35 \
  --region ap-southeast-1 \
  --zones ap-southeast-1a,ap-southeast-1b \
  --without-nodegroup


##  Create Node Group
eksctl create nodegroup \
  --cluster=todo-cluster \
  --name=todo-nodes \
  --region=ap-southeast-1 \
  --node-type=t3.medium \
  --managed \
  --nodes=2 \
  --nodes-min=2 \
  --nodes-max=3


##  Create Kubernetes Namespace
kubectl create namespace shopverce


### Verify all pods are running:
kubectl get pods -n shopverce

### Verify the Deployment
kubectl get all -n shopverce



## Configure credentials
kubectl apply -f k8s/db-secrets.yaml
kubectl apply -f k8s/app-configmap.yaml



## Deploy Database
kubectl apply -f k8s/postgres-user.yaml
kubectl apply -f k8s/postgres-inventory.yaml
kubectl apply -f k8s/mongodb-product.yaml
kubectl apply -f k8s/mongodb-order.yaml
kubectl apply -f k8s/redis-service.yaml




## Deploy All Application Services
kubectl apply -f k8s/frontend.yaml


### Wait for the LoadBalancer to get an external hostname
kubectl get svc frontend -n shopverce -w

### Once the EXTERNAL-IP column changes from <pending> to a hostname, press Ctrl+C and save it:
export APP_URL=$(kubectl get svc frontend -n shopverce -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "Application URL: http://$APP_URL"


kubectl apply -f k8s/user-service.yaml
kubectl apply -f k8s/product-service.yaml
kubectl apply -f k8s/order-service.yaml
kubectl apply -f k8s/inventory-service.yaml


## Deploy the Nginx Gateway
kubectl apply -f k8s/nginx-configmap.yaml
kubectl apply -f k8s/nginx-gateway.yaml

Build and deploy the React frontend. The image serves the built app and proxies /api to the services above.

docker build -f frontend/Dockerfile -t swapno/shopverse-frontend:latest .
docker push swapno/shopverse-frontend:latest
kubectl apply -f k8s/frontend.yaml
















## Restart services
kubectl rollout restart deployment -n shopverce 