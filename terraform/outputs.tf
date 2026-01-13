# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = module.vpc.vpc_cidr
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = module.vpc.public_subnet_ids
}

# EKS Cluster Outputs
output "cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Endpoint for EKS cluster API server"
  value       = module.eks.cluster_endpoint
}

output "cluster_version" {
  description = "Kubernetes version of the cluster"
  value       = module.eks.cluster_version
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data for cluster authentication"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "cluster_oidc_issuer_url" {
  description = "OIDC issuer URL for the cluster"
  value       = module.eks.cluster_oidc_issuer_url
}

output "oidc_provider_arn" {
  description = "ARN of the OIDC provider for IRSA"
  value       = module.eks.oidc_provider_arn
}

# Node Group Outputs
output "node_group_id" {
  description = "ID of the EKS node group"
  value       = module.node_group.node_group_id
}

output "node_group_status" {
  description = "Status of the EKS node group"
  value       = module.node_group.node_group_status
}

output "autoscaling_group_names" {
  description = "Names of the Auto Scaling Groups"
  value       = module.node_group.autoscaling_group_names
}

# IAM Outputs
output "cluster_role_arn" {
  description = "ARN of the EKS cluster IAM role"
  value       = module.iam.cluster_role_arn
}

output "node_group_role_arn" {
  description = "ARN of the EKS node group IAM role"
  value       = module.iam.node_group_role_arn
}

output "pod_execution_role_arn" {
  description = "ARN of the pod execution IAM role (IRSA - if created)"
  value       = module.iam.pod_execution_role_arn
}

# Security Group Outputs
output "cluster_security_group_id" {
  description = "ID of the EKS cluster security group"
  value       = module.security_groups.cluster_security_group_id
}

output "node_security_group_id" {
  description = "ID of the EKS node group security group"
  value       = module.security_groups.node_security_group_id
}

output "alb_security_group_id" {
  description = "ID of the Application Load Balancer security group"
  value       = module.security_groups.alb_security_group_id
}

# Kubeconfig Command
output "configure_kubectl" {
  description = "Command to configure kubectl for the EKS cluster"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name} --profile ${var.aws_profile}"
}

# In-Cluster Services Note
output "in_cluster_services" {
  description = "Services running inside the Kubernetes cluster"
  value = {
    note        = "MinIO and Valkey/Redis run as in-cluster services. Deploy them using Helm or Kustomize."
    redis_host  = "redis-service (ClusterIP service in hivebox namespace)"
    redis_port  = 6379
    minio_host  = "minio-service (ClusterIP service in hivebox namespace)"
    minio_port  = 9000
    namespace   = var.kubernetes_namespace
  }
}
