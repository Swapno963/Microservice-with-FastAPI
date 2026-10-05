resource "aws_cloudwatch_metric_alarm" "alb_target_5xx" {
  count = local.frontend_alb_suffix == null ? 0 : 1

  alarm_name          = "shopverce-alb-target-5xx"
  alarm_description   = "Targets behind the frontend ALB returned more than 10 HTTP 5xx responses in 5 minutes."
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]

  dimensions = {
    LoadBalancer = local.frontend_alb_suffix
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_elb_5xx" {
  count = local.frontend_alb_suffix == null ? 0 : 1

  alarm_name          = "shopverce-alb-elb-5xx"
  alarm_description   = "The frontend ALB itself returned more than 10 HTTP 5xx responses in 5 minutes."
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "HTTPCode_ELB_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]

  dimensions = {
    LoadBalancer = local.frontend_alb_suffix
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_latency" {
  count = local.frontend_alb_suffix == null ? 0 : 1

  alarm_name          = "shopverce-alb-latency"
  alarm_description   = "Average frontend ALB target response time is above 1 second."
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Average"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]

  dimensions = {
    LoadBalancer = local.frontend_alb_suffix
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_unhealthy_targets" {
  for_each = local.frontend_target_group_suffixes

  alarm_name          = "shopverce-alb-unhealthy-targets-${substr(sha1(each.key), 0, 8)}"
  alarm_description   = "The frontend ALB has at least one unhealthy target."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Maximum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]

  dimensions = {
    LoadBalancer = local.frontend_alb_suffix
    TargetGroup  = each.value
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_request_anomaly" {
  count = local.frontend_alb_suffix == null ? 0 : 1

  alarm_name          = "shopverce-alb-request-count-anomaly"
  alarm_description   = "Frontend ALB request count is outside the 2 standard deviation band."
  comparison_operator = "LessThanLowerOrGreaterThanUpperThreshold"
  evaluation_periods  = 2
  threshold_metric_id = "band"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]

  metric_query {
    id          = "band"
    expression  = "ANOMALY_DETECTION_BAND(requests, 2)"
    label       = "RequestCount band"
    return_data = true
  }

  metric_query {
    id          = "requests"
    return_data = true

    metric {
      metric_name = "RequestCount"
      namespace   = "AWS/ApplicationELB"
      period      = 300
      stat        = "Sum"

      dimensions = {
        LoadBalancer = local.frontend_alb_suffix
      }
    }
  }
}
