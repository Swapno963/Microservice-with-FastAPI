resource "aws_eks_addon" "cloudwatch_observability" {
  cluster_name                = var.cluster_name
  addon_name                  = "amazon-cloudwatch-observability"
  addon_version               = local.cloudwatch_addon_version
  service_account_role_arn    = aws_iam_role.cloudwatch_agent.arn
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  depends_on = [aws_iam_role_policy_attachment.cloudwatch_agent]

  # Enhanced Container Insights for node CPU, memory, disk, and pressure.
  # Application log shipping and Application Signals stay off; those belong
  # to Loki and OpenTelemetry.
  configuration_values = jsonencode({
    agent = {
      config = {
        logs = {
          metrics_collected = {
            kubernetes = {
              enhanced_container_insights = true
            }
          }
        }
      }
    }
    containerLogs = {
      enabled = false
    }
    applicationSignals = {
      enabled = false
    }
  })
}
