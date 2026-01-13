# HiveBox EKS Terraform Infrastructure

This directory contains Terraform modules for deploying the HiveBox application infrastructure on AWS using Amazon EKS (Elastic Kubernetes Service).

## Architecture Overview

The infrastructure creates:

- **VPC**: Multi-AZ VPC with public and private subnets, NAT Gateways, and Internet Gateway
- **EKS Cluster**: Managed Kubernetes control plane with configurable logging and addons
- **EKS Node Group**: Auto-scaling worker nodes with customizable instance types
- **Security Groups**: Network security for cluster, nodes, and load balancer
- **IAM Roles**: Proper IAM roles for cluster and nodes, with optional IRSA support

**In-Cluster Services** (deployed via Helm/Kustomize):
- **Valkey/Redis**: Runs as a deployment inside the cluster (redis-service)
- **MinIO**: Runs as a deployment inside the cluster (minio-service)
- **HiveBox Application**: Your Flask application with all components

## Module Structure

```
terraform/
├── main.tf                    # Root module configuration
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── terraform.tfvars.example   # Example configuration values
├── README.md                  # This file
└── modules/
    ├── vpc/                   # VPC and networking
    ├── eks/                   # EKS cluster
    ├── node-group/            # EKS node group
    ├── security-groups/       # Security groups
    └── iam/                   # IAM roles and policies
```

## Prerequisites

Before deploying, ensure you have:

1. **AWS CLI** configured with appropriate credentials
   ```bash
   aws configure --profile Gabriel-Admin
   ```

2. **Terraform** version >= 1.5.0
   ```bash
   terraform version
   ```

3. **kubectl** for Kubernetes management
   ```bash
   kubectl version --client
   ```

4. **Sufficient AWS permissions** to create VPC, EKS, IAM roles, and security groups

## Quick Start

### 1. Configure Variables

```bash
cd terraform

# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit configuration
# Update these values in terraform.tfvars:
# - cluster_public_access_cidrs: Restrict to your IP for security
# - common_tags: Add your team/owner information
```

### 2. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Review planned changes
terraform plan

# Deploy infrastructure
terraform apply
# Type 'yes' when prompted
```

**Deployment time:** 15-20 minutes

### 3. Configure kubectl

After deployment completes:

```bash
# Use the output command
terraform output -raw configure_kubectl | bash

# Or manually
aws eks update-kubeconfig \
  --region us-east-2 \
  --name hivebox-eks \
  --profile Gabriel-Admin

# Verify access
kubectl get nodes
```

### 4. Deploy HiveBox Application

The Terraform infrastructure only creates the EKS cluster. Your application components run inside Kubernetes.

#### Using Helm

```bash
cd ../helm-chart

helm upgrade --install hivebox . --namespace hivebox --create-namespace
```

#### Using Kustomize

```bash
cd ../kustomize

# For production
kubectl apply -k overlays/prod

# For staging
kubectl apply -k overlays/staging
```

#### Verify Deployment

```bash
# Check all resources
kubectl get all -n hivebox

# Check pods
kubectl get pods -n hivebox

# Expected pods:
# - hivebox-app (2 replicas)
# - redis/valkey (1 replica)
# - minio (1 replica)

# View logs
kubectl logs -n hivebox -l app=hivebox --tail=50
```

## Architecture Details

### Network Architecture

```
Internet
   │
   ▼
┌─────────────────┐
│ Internet Gateway│
└────────┬────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ Public Subnets (2 AZs)               │
│ - NAT Gateways                       │
└────────┬─────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ Private Subnets (2 AZs)              │
│ - EKS Worker Nodes                   │
│   - HiveBox Pods                     │
│   - Redis/Valkey Pods               │
│   - MinIO Pods                       │
└──────────────────────────────────────┘
```

### In-Cluster Services

All application components run inside Kubernetes:

| Service | Type | Port | Purpose |
|---------|------|------|---------|
| **HiveBox** | Deployment (2 replicas) | 5000 | Main Flask application |
| **Valkey/Redis** | Deployment (1 replica) | 6379 | In-memory caching |
| **MinIO** | Deployment (1 replica) | 9000 | Object storage |

Communication between services uses Kubernetes ClusterIP services (DNS-based service discovery).

## Important Configuration Variables

### EKS Cluster

| Variable | Default | Description |
|----------|---------|-------------|
| `cluster_name` | `hivebox-eks` | Name of the EKS cluster |
| `kubernetes_version` | `1.31` | Kubernetes version |
| `cluster_endpoint_public_access` | `true` | Enable public API endpoint |
| `cluster_public_access_cidrs` | `["0.0.0.0/0"]` | IPs allowed to access API |

### Node Group

| Variable | Default | Description |
|----------|---------|-------------|
| `node_group_desired_size` | `2` | Desired number of nodes |
| `node_group_min_size` | `1` | Minimum nodes |
| `node_group_max_size` | `4` | Maximum nodes |
| `node_group_instance_types` | `["t3.medium"]` | EC2 instance types |

## Outputs

After deployment, view outputs:

```bash
# View all outputs
terraform output

# Important outputs:
terraform output cluster_name
terraform output cluster_endpoint
terraform output in_cluster_services
```

## Infrastructure Costs

### Current Configuration (~$140/month)
- **EKS Cluster**: $73/month (control plane)
- **2x t3.medium instances**: ~$60/month
- **2x NAT Gateways**: ~$65/month
- **Data Transfer**: ~$5/month
- **Total**: ~$203/month

### Cost Optimization Tips

For development/testing:

```hcl
# Use smaller instances
node_group_instance_types = ["t3.small"]

# Use SPOT instances (save 70%)
node_group_capacity_type = "SPOT"

# Reduce node count
node_group_desired_size = 1
node_group_min_size = 1
```

## Cleanup

To destroy all resources:

```bash
cd terraform

# IMPORTANT: Delete Kubernetes resources first
kubectl delete namespace hivebox

# Destroy Terraform infrastructure
terraform destroy
# Type 'yes' when prompted
```

**Warning:** This is irreversible. Ensure you have backups of any important data.

## Security Best Practices

1. **Restrict API Access**: Update `cluster_public_access_cidrs` to your IP
   ```hcl
   cluster_public_access_cidrs = ["YOUR_IP/32"]
   ```

2. **Use Private Subnets**: EKS nodes run in private subnets by default

3. **Enable Logging**: All control plane logs are enabled for auditing

4. **IAM Roles**: Least privilege IAM roles for cluster and nodes

## Troubleshooting

### Cannot create cluster

**Error**: `Error creating EKS Cluster`

**Solution**: Check AWS credentials and IAM permissions

### Nodes not joining cluster

**Solution**:
1. Verify security groups allow communication
2. Check IAM role has required policies
3. Verify VPC CNI addon is installed

```bash
kubectl get pods -n kube-system | grep aws-node
```

### Application cannot connect to Redis/MinIO

**Solution**: Ensure services are deployed and running

```bash
# Check services
kubectl get svc -n hivebox

# Should see:
# - hivebox-service
# - redis-service
# - minio-service

# Check pods
kubectl get pods -n hivebox
```

## Maintenance

### Updating Kubernetes Version

1. Update `kubernetes_version` in `terraform.tfvars`
2. Apply changes:
   ```bash
   terraform apply
   ```

**Note**: Upgrade one minor version at a time (1.30 → 1.31).

### Scaling Nodes

Update node count:

```hcl
node_group_desired_size = 3
```

Then apply:
```bash
terraform apply
```

## Additional Resources

- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

## Support

For issues or questions:
1. Check Terraform plan output
2. Review CloudWatch logs
3. Verify AWS service quotas
4. Consult module documentation in `modules/*/`

## License

This infrastructure code is part of the HiveBox project.
