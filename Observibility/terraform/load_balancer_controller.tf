resource "helm_release" "aws_load_balancer_controller" {
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  version    = "3.5.0"
  namespace  = "kube-system"

  depends_on = [aws_iam_role_policy_attachment.lb_controller]

  values = [
    yamlencode({
      clusterName = var.cluster_name
      region      = var.region
      vpcId       = data.aws_eks_cluster.this.vpc_config[0].vpc_id
      serviceAccount = {
        create = true
        name   = "aws-load-balancer-controller"
        annotations = {
          "eks.amazonaws.com/role-arn" = aws_iam_role.lb_controller.arn
        }
      }
    })
  ]
}
