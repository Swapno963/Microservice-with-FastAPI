variable "region" {
  description = "AWS region of the existing EKS cluster."
  type        = string
  default     = "ap-southeast-1"
}

variable "cluster_name" {
  description = "EKS cluster created with eksctl. Terraform does not create this cluster."
  type        = string
  default     = "todo-cluster"
}

variable "nodegroup_name" {
  description = "EKS managed node group to alarm on."
  type        = string
  default     = "todo-nodes"
}

variable "namespace" {
  description = "Namespace of the frontend Ingress."
  type        = string
  default     = "shopverce"
}

variable "ingress_name" {
  description = "Ingress name. The AWS Load Balancer Controller tags the ALB with namespace/name."
  type        = string
  default     = "frontend"
}

variable "alarm_email" {
  description = "Optional address subscribed to infrastructure alarms. Leave empty to keep the SNS topic without an email subscription."
  type        = string
  default     = ""
}
