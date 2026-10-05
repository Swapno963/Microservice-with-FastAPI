resource "aws_cloudwatch_metric_alarm" "node_cpu" {
  for_each = local.node_asg_names

  alarm_name          = "shopverce-node-cpu-${each.value}"
  alarm_description   = "EKS node group CPU is above 80 percent."
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]

  dimensions = {
    AutoScalingGroupName = each.value
  }
}

resource "aws_cloudwatch_metric_alarm" "node_status_check" {
  for_each = local.node_asg_names

  alarm_name          = "shopverce-node-status-${each.value}"
  alarm_description   = "An EKS node failed an EC2 status check."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]

  dimensions = {
    AutoScalingGroupName = each.value
  }
}

resource "aws_cloudwatch_metric_alarm" "node_ebs_status" {
  for_each = local.node_asg_names

  alarm_name          = "shopverce-node-ebs-${each.value}"
  alarm_description   = "An EKS node failed the attached EBS status check."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed_AttachedEBS"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]

  dimensions = {
    AutoScalingGroupName = each.value
  }
}

locals {
  container_insights_alarms = {
    memory = {
      metric      = "node_memory_utilization"
      statistic   = "Average"
      reducer     = "MAX"
      operator    = "GreaterThanThreshold"
      threshold   = 80
      description = "A node is using more than 80 percent of its memory."
    }
    filesystem = {
      metric      = "node_filesystem_utilization"
      statistic   = "Average"
      reducer     = "MAX"
      operator    = "GreaterThanThreshold"
      threshold   = 80
      description = "A node filesystem is more than 80 percent full."
    }
    disk_pressure = {
      metric      = "node_status_condition_disk_pressure"
      statistic   = "Maximum"
      reducer     = "MAX"
      operator    = "GreaterThanThreshold"
      threshold   = 0
      description = "A node reports disk pressure."
    }
    memory_pressure = {
      metric      = "node_status_condition_memory_pressure"
      statistic   = "Maximum"
      reducer     = "MAX"
      operator    = "GreaterThanThreshold"
      threshold   = 0
      description = "A node reports memory pressure."
    }
    not_ready = {
      metric      = "node_status_condition_ready"
      statistic   = "Minimum"
      reducer     = "MIN"
      operator    = "LessThanThreshold"
      threshold   = 1
      description = "A node is not Ready."
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "container_insights" {
  for_each = local.container_insights_alarms

  alarm_name          = "shopverce-node-${replace(each.key, "_", "-")}"
  alarm_description   = each.value.description
  comparison_operator = each.value.operator
  evaluation_periods  = 2
  threshold           = each.value.threshold
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]

  metric_query {
    id          = "nodes"
    expression  = "${each.value.reducer}(SEARCH('{ContainerInsights,ClusterName,InstanceId,NodeName} MetricName=\"${each.value.metric}\" ClusterName=\"${var.cluster_name}\"', '${each.value.statistic}', 300))"
    label       = each.value.metric
    return_data = true
  }
}
