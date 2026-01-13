variable "bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
}

variable "force_destroy" {
  description = "Allow bucket to be destroyed even if it contains objects"
  type        = bool
  default     = false
}

variable "versioning_enabled" {
  description = "Enable bucket versioning"
  type        = bool
  default     = true
}

variable "kms_key_id" {
  description = "KMS key ID for encryption (optional, uses AES256 if not specified)"
  type        = string
  default     = ""
}

variable "block_public_access" {
  description = "Block all public access to the bucket"
  type        = bool
  default     = true
}

variable "enable_lifecycle_rules" {
  description = "Enable lifecycle rules for data management"
  type        = bool
  default     = true
}

variable "lifecycle_prefix" {
  description = "Prefix for lifecycle rules"
  type        = string
  default     = ""
}

variable "transition_to_ia_days" {
  description = "Days until transition to Infrequent Access storage"
  type        = number
  default     = 30
}

variable "transition_to_glacier_days" {
  description = "Days until transition to Glacier storage"
  type        = number
  default     = 90
}

variable "enable_expiration" {
  description = "Enable object expiration"
  type        = bool
  default     = false
}

variable "expiration_days" {
  description = "Days until objects expire (deleted)"
  type        = number
  default     = 365
}

variable "enable_cors" {
  description = "Enable CORS configuration"
  type        = bool
  default     = false
}

variable "cors_allowed_headers" {
  description = "List of allowed headers for CORS"
  type        = list(string)
  default     = ["*"]
}

variable "cors_allowed_methods" {
  description = "List of allowed methods for CORS"
  type        = list(string)
  default     = ["GET", "PUT", "POST", "DELETE"]
}

variable "cors_allowed_origins" {
  description = "List of allowed origins for CORS"
  type        = list(string)
  default     = ["*"]
}

variable "cors_expose_headers" {
  description = "List of headers to expose in CORS"
  type        = list(string)
  default     = ["ETag"]
}

variable "cors_max_age_seconds" {
  description = "Max age for CORS preflight requests"
  type        = number
  default     = 3000
}

variable "additional_policy_statements" {
  description = "Additional IAM policy statements for bucket policy"
  type = list(object({
    sid       = string
    effect    = string
    actions   = list(string)
    resources = list(string)
    principals = list(object({
      type        = string
      identifiers = list(string)
    }))
    conditions = optional(list(object({
      test     = string
      variable = string
      values   = list(string)
    })))
  }))
  default = []
}

variable "enable_logging" {
  description = "Enable S3 access logging"
  type        = bool
  default     = false
}

variable "enable_metrics" {
  description = "Enable CloudWatch metrics"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
