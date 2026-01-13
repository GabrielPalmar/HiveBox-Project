variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "oidc_provider_arn" {
  description = "ARN of the OIDC provider for IRSA"
  type        = string
  default     = ""
}

variable "namespace" {
  description = "Kubernetes namespace for the application"
  type        = string
  default     = "hivebox"
}

variable "service_account_name" {
  description = "Name of the Kubernetes service account"
  type        = string
  default     = "hivebox-sa"
}

variable "create_irsa_role" {
  description = "Whether to create IRSA role for service accounts"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
