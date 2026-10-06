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

output "cloudwatch_agent_role_arn" {
  description = "IRSA role annotated onto amazon-cloudwatch/cloudwatch-agent by the CloudWatch Observability add-on."
  value       = aws_iam_role.cloudwatch_agent.arn
}

output "cloudwatch_agent_irsa_subject" {
  description = "OIDC subject the CloudWatch agent role trusts. Must stay equal to the add-on service account."
  value       = local.cloudwatch_agent_irsa_subject
}

output "frontend_alb_dimension" {
  description = "CloudWatch LoadBalancer dimension. Null until the frontend Ingress exists and Terraform is applied again."
  value       = local.frontend_alb_suffix
}
