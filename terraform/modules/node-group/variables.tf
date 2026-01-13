variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "node_role_arn" {
  description = "ARN of the IAM role for node group"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for node group"
  type        = list(string)
}

variable "kubernetes_version" {
  description = "Kubernetes version for node group"
  type        = string
  default     = null
}

variable "desired_size" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 2
}

variable "max_size" {
  description = "Maximum number of worker nodes"
  type        = number
  default     = 4
}

variable "min_size" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 1
}

variable "max_unavailable_percentage" {
  description = "Maximum percentage of nodes unavailable during update"
  type        = number
  default     = 33
}

variable "instance_types" {
  description = "List of instance types for node group"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "capacity_type" {
  description = "Type of capacity (ON_DEMAND or SPOT)"
  type        = string
  default     = "ON_DEMAND"
}

variable "disk_size" {
  description = "Disk size in GiB for worker nodes"
  type        = number
  default     = 20
}

variable "ec2_ssh_key" {
  description = "EC2 Key Pair name for SSH access to nodes"
  type        = string
  default     = ""
}

variable "ssh_security_group_ids" {
  description = "List of security group IDs allowed to SSH to nodes"
  type        = list(string)
  default     = []
}

variable "launch_template_id" {
  description = "ID of custom launch template (optional)"
  type        = string
  default     = ""
}

variable "launch_template_version" {
  description = "Version of launch template to use"
  type        = string
  default     = "$Latest"
}

variable "labels" {
  description = "Kubernetes labels to apply to nodes"
  type        = map(string)
  default     = {}
}

variable "taints" {
  description = "List of Kubernetes taints to apply to nodes"
  type = list(object({
    key    = string
    value  = string
    effect = string
  }))
  default = []
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
