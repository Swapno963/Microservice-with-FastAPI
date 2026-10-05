output "sns_topic_arn" {
  description = "Topic that receives infrastructure alarms and AWS events."
  value       = aws_sns_topic.alarms.arn
}

output "eks_log_group" {
  description = "EKS control plane log group."
  value       = aws_cloudwatch_log_group.eks.name
}

output "load_balancer_controller_role_arn" {
  description = "IRSA role used by the AWS Load Balancer Controller."
  value       = aws_iam_role.lb_controller.arn
}

output "frontend_alb_dimension" {
  description = "CloudWatch LoadBalancer dimension. Null until the frontend Ingress exists and Terraform is applied again."
  value       = local.frontend_alb_suffix
}
