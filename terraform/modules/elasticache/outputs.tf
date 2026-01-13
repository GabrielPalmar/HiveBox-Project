output "redis_endpoint" {
  description = "Primary endpoint for Redis cluster"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "redis_port" {
  description = "Port number for Redis"
  value       = aws_elasticache_replication_group.redis.port
}

output "redis_reader_endpoint" {
  description = "Reader endpoint for Redis cluster (for read replicas)"
  value       = aws_elasticache_replication_group.redis.reader_endpoint_address
}

output "redis_configuration_endpoint" {
  description = "Configuration endpoint for Redis cluster (cluster mode enabled)"
  value       = aws_elasticache_replication_group.redis.configuration_endpoint_address
}

output "redis_replication_group_id" {
  description = "ID of the Redis replication group"
  value       = aws_elasticache_replication_group.redis.id
}

output "redis_replication_group_arn" {
  description = "ARN of the Redis replication group"
  value       = aws_elasticache_replication_group.redis.arn
}

output "redis_member_clusters" {
  description = "List of member cluster IDs"
  value       = aws_elasticache_replication_group.redis.member_clusters
}
