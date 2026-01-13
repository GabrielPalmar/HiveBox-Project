terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # Optional: Configure S3 backend for state management
  # Uncomment and configure this after creating the backend resources
  # backend "s3" {
  #   bucket         = "hivebox-terraform-state"
  #   key            = "eks/terraform.tfstate"
  #   region         = "us-east-2"
  #   encrypt        = true
  #   dynamodb_table = "terraform-state-lock"
  # }
}

# Configure the AWS Provider
provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile

  default_tags {
    tags = var.common_tags
  }
}

# Local variables
locals {
  cluster_name = var.cluster_name

  common_tags = merge(
    var.common_tags,
    {
      ManagedBy = "Terraform"
      Project   = "HiveBox"
    }
  )
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  cluster_name             = local.cluster_name
  vpc_cidr                 = var.vpc_cidr
  availability_zones_count = var.availability_zones_count
  tags                     = local.common_tags
}

# IAM Roles Module (must be created before EKS)
module "iam" {
  source = "./modules/iam"

  cluster_name         = local.cluster_name
  oidc_provider_arn    = ""  # Will be populated after EKS cluster creation
  namespace            = var.kubernetes_namespace
  service_account_name = var.kubernetes_service_account
  create_irsa_role     = var.create_irsa_role
  tags                 = local.common_tags
}

# Security Groups Module
module "security_groups" {
  source = "./modules/security-groups"

  cluster_name = local.cluster_name
  vpc_id       = module.vpc.vpc_id
  tags         = local.common_tags

  depends_on = [module.vpc]
}

# EKS Cluster Module
module "eks" {
  source = "./modules/eks"

  cluster_name               = local.cluster_name
  cluster_version            = var.kubernetes_version
  cluster_role_arn           = module.iam.cluster_role_arn
  private_subnet_ids         = module.vpc.private_subnet_ids
  public_subnet_ids          = module.vpc.public_subnet_ids
  cluster_security_group_id  = module.security_groups.cluster_security_group_id
  endpoint_private_access    = var.cluster_endpoint_private_access
  endpoint_public_access     = var.cluster_endpoint_public_access
  public_access_cidrs        = var.cluster_public_access_cidrs
  enabled_cluster_log_types  = var.cluster_log_types
  tags                       = local.common_tags

  depends_on = [module.vpc, module.iam, module.security_groups]
}

# EKS Node Group Module
module "node_group" {
  source = "./modules/node-group"

  cluster_name       = module.eks.cluster_name
  node_role_arn      = module.iam.node_group_role_arn
  subnet_ids         = module.vpc.private_subnet_ids
  kubernetes_version = var.kubernetes_version
  desired_size       = var.node_group_desired_size
  max_size           = var.node_group_max_size
  min_size           = var.node_group_min_size
  instance_types     = var.node_group_instance_types
  capacity_type      = var.node_group_capacity_type
  disk_size          = var.node_group_disk_size
  tags               = local.common_tags

  depends_on = [module.eks]
}

# Note: MinIO and Valkey/Redis will be deployed as in-cluster Kubernetes resources
# using your existing Helm charts or Kustomize manifests.
# No AWS ElastiCache or S3 resources are created by this Terraform configuration.
