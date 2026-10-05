resource "aws_cloudwatch_event_rule" "health" {
  name        = "shopverce-aws-health"
  description = "AWS Health events for EKS, EC2, and Elastic Load Balancing."

  event_pattern = jsonencode({
    source      = ["aws.health"]
    detail-type = ["AWS Health Event"]
    detail = {
      service = ["EKS", "EC2", "ELASTICLOADBALANCING", "ELB"]
    }
  })
}

resource "aws_cloudwatch_event_target" "health" {
  rule      = aws_cloudwatch_event_rule.health.name
  target_id = "sns"
  arn       = aws_sns_topic.alarms.arn

  depends_on = [aws_sns_topic_policy.alarms]
}

resource "aws_cloudwatch_event_rule" "autoscaling" {
  name        = "shopverce-node-launch-failures"
  description = "Node group instances that fail to launch or terminate."

  event_pattern = jsonencode({
    source      = ["aws.autoscaling"]
    detail-type = ["EC2 Instance Launch Unsuccessful", "EC2 Instance Terminate Unsuccessful"]
    detail = {
      AutoScalingGroupName = tolist(local.node_asg_names)
    }
  })
}

resource "aws_cloudwatch_event_target" "autoscaling" {
  rule      = aws_cloudwatch_event_rule.autoscaling.name
  target_id = "sns"
  arn       = aws_sns_topic.alarms.arn

  depends_on = [aws_sns_topic_policy.alarms]
}
