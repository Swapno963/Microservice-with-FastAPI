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
      operator    = "GreaterThanThreshold"
      threshold   = 80
      description = "A node is using more than 80 percent of its memory."
    }
    filesystem = {
      metric      = "node_filesystem_utilization"
      statistic   = "Average"
      operator    = "GreaterThanThreshold"
      threshold   = 80
      description = "A node filesystem is more than 80 percent full."
    }
    disk_pressure = {
      metric      = "node_status_condition_disk_pressure"
      statistic   = "Maximum"
      operator    = "GreaterThanThreshold"
      threshold   = 0
      description = "A node reports disk pressure."
    }
    memory_pressure = {
      metric      = "node_status_condition_memory_pressure"
      statistic   = "Maximum"
      operator    = "GreaterThanThreshold"
      threshold   = 0
      description = "A node reports memory pressure."
    }
    not_ready = {
      metric      = "node_status_condition_ready"
      statistic   = "Minimum"
      operator    = "LessThanThreshold"
      threshold   = 1
      description = "A node is not Ready."
    }
  }

  # Metric alarms cannot use SEARCH. One alarm per running node uses the
  # Container Insights dimensions ClusterName, InstanceId, and NodeName.
  node_container_insights_alarms = {
    for item in flatten([
      for instance_id, instance in data.aws_instance.node : [
        for alarm_key, alarm in local.container_insights_alarms : {
          key         = "${alarm_key}-${instance_id}"
          alarm_key   = alarm_key
          metric      = alarm.metric
          statistic   = alarm.statistic
          operator    = alarm.operator
          threshold   = alarm.threshold
          description = alarm.description
          instance_id = instance_id
          node_name   = instance.private_dns
        }
      ]
    ]) : item.key => item
  }
}

resource "aws_cloudwatch_metric_alarm" "container_insights" {
  for_each = local.node_container_insights_alarms

  alarm_name          = "shopverce-node-${replace(each.value.alarm_key, "_", "-")}-${each.value.instance_id}"
  alarm_description   = each.value.description
  comparison_operator = each.value.operator
  evaluation_periods  = 2
  metric_name         = each.value.metric
  namespace           = "ContainerInsights"
  period              = 300
  statistic           = each.value.statistic
  threshold           = each.value.threshold
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]

  dimensions = {
    ClusterName = var.cluster_name
    InstanceId  = each.value.instance_id
    NodeName    = each.value.node_name
  }
}
