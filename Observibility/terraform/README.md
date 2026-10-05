# CloudWatch infrastructure monitoring

Terraform manages CloudWatch, the AWS Load Balancer Controller, and the alarms for the existing eksctl cluster. It does not create or replace `todo-cluster`.

Defaults match the cluster in `k8s/DEPLOY-INSTRUCTIONS.MD`:

- region `ap-southeast-1`
- cluster `todo-cluster`
- node group `todo-nodes`
- namespace `shopverce`

## Prerequisite

The cluster needs an IAM OIDC provider so the controller and the CloudWatch agent can use IRSA. Confirm it:

```bash
aws eks describe-cluster --name todo-cluster --region ap-southeast-1 \
  --query cluster.identity.oidc.issuer
```

If that query returns `null`, create the provider before `terraform apply`:

```bash
eksctl utils associate-iam-oidc-provider \
  --cluster todo-cluster \
  --region ap-southeast-1 \
  --approve
```

The public subnets must be tagged so the controller can place an internet-facing load balancer. eksctl does this. Confirm at least one subnet has both tags:

- `kubernetes.io/cluster/todo-cluster` = `shared` or `owned`
- `kubernetes.io/role/elb` = `1`

```bash
aws ec2 describe-subnets --region ap-southeast-1 \
  --filters Name=tag:kubernetes.io/role/elb,Values=1 \
  --query 'Subnets[].SubnetId'
```

## Apply

From the repository root:

```bash
cd Observibility/terraform
terraform init
terraform apply
```

The first apply installs the AWS Load Balancer Controller, enables EKS control plane logs (`api`, `audit`, `authenticator`, `controllerManager`, `scheduler`) in `/aws/eks/todo-cluster/cluster`, installs the CloudWatch Observability add-on, and creates node alarms plus the SNS topic `shopverce-infra-alarms`.

Application container logs and Application Signals stay disabled. Those belong to Loki and OpenTelemetry.

Set an email only if you want a subscription. AWS will send a confirmation message:

```bash
terraform apply -var='alarm_email=you@example.com'
```

## Frontend Ingress

After the controller is running, apply the frontend. The Service is `ClusterIP`; the Ingress creates the Application Load Balancer and removes the old Classic load balancer.

```bash
kubectl apply -f k8s/frontend.yaml
kubectl get ingress frontend -n shopverce -w
```

Wait until `ADDRESS` is populated.

## Second apply

ALB alarms are created only after the load balancer exists. The controller tags it with `ingress.k8s.aws/stack=shopverce/frontend`. Run apply again:

```bash
terraform apply
```

`frontend_alb_dimension` is empty until that second apply. The alarms cover target and load-balancer HTTP 5xx, target response time, unhealthy targets, and request-count anomaly detection.
