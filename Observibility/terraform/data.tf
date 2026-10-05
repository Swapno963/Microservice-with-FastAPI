data "aws_caller_identity" "current" {}

data "aws_eks_cluster" "this" {
  name = var.cluster_name
}

data "tls_certificate" "eks" {
  url = data.aws_eks_cluster.this.identity[0].oidc[0].issuer
}

data "aws_autoscaling_groups" "nodes" {
  filter {
    name   = "tag:eks:cluster-name"
    values = [var.cluster_name]
  }

  filter {
    name   = "tag:eks:nodegroup-name"
    values = [var.nodegroup_name]
  }
}

data "aws_lbs" "frontend" {
  tags = {
    "ingress.k8s.aws/stack" = "${var.namespace}/${var.ingress_name}"
  }
}

data "aws_resourcegroupstaggingapi_resources" "frontend_target_groups" {
  resource_type_filters = ["elasticloadbalancing:targetgroup"]

  tag_filter {
    key    = "ingress.k8s.aws/stack"
    values = ["${var.namespace}/${var.ingress_name}"]
  }
}

locals {
  oidc_host      = replace(aws_iam_openid_connect_provider.eks.url, "https://", "")
  node_asg_names = toset(data.aws_autoscaling_groups.nodes.names)

  frontend_alb_arns   = sort(data.aws_lbs.frontend.arns)
  frontend_alb_suffix = length(local.frontend_alb_arns) > 0 ? regex("loadbalancer/(.+)$", local.frontend_alb_arns[0])[0] : null

  # UnHealthyHostCount requires both the load balancer and target group dimensions.
  frontend_target_group_suffixes = local.frontend_alb_suffix == null ? {} : {
    for resource in data.aws_resourcegroupstaggingapi_resources.frontend_target_groups.resource_tag_mapping_list :
    resource.resource_arn => regex(":(targetgroup/.+)$", resource.resource_arn)[0]
  }
}
