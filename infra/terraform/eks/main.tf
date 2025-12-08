resource "aws_eks_cluster" "cluster" {
  name     = "mycluster"
  role_arn = var.cluster_role_arn

  vpc_config {
    subnet_ids             = var.private_subnets
    endpoint_public_access = true
  }
}

resource "aws_eks_node_group" "nodes" {
  cluster_name  = aws_eks_cluster.cluster.name
  node_role_arn = var.node_role_arn
  subnet_ids    = var.private_subnets

  scaling_config {
    desired_size = 2
    max_size     = 3
    min_size     = 1
  }

  depends_on = [
    aws_eks_cluster.cluster
  ]
}
