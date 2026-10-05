resource "aws_cloudwatch_log_group" "eks" {
  name              = "/aws/eks/${var.cluster_name}/cluster"
  retention_in_days = 7
}

resource "terraform_data" "eks_control_plane_logs" {
  depends_on = [aws_cloudwatch_log_group.eks]

  input = {
    cluster_name = var.cluster_name
    region       = var.region
  }

  provisioner "local-exec" {
    interpreter = ["bash", "-c"]
    command     = <<-EOT
      set -o pipefail
      logging='{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
      set +e
      output=$(aws eks update-cluster-config --name "$CLUSTER" --region "$REGION" --logging "$logging" 2>&1)
      status=$?
      set -e
      if [ "$status" -ne 0 ]; then
        if printf '%s' "$output" | grep -Eqi 'already|no changes'; then
          echo "Control plane logging already matches the desired configuration"
          exit 0
        fi
        printf '%s\n' "$output" >&2
        exit "$status"
      fi
      printf '%s\n' "$output"
    EOT

    environment = {
      CLUSTER = var.cluster_name
      REGION  = var.region
    }
  }
}
