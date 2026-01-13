# ElastiCache Redis Module
# Replaces the in-cluster Valkey/Redis deployment

resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.cluster_name}-redis-subnet-group"
  subnet_ids = var.subnet_ids

  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-redis-subnet-group"
    }
  )
}

resource "aws_elasticache_parameter_group" "redis" {
  name   = "${var.cluster_name}-redis-params"
  family = var.parameter_group_family

  # Custom parameters based on application requirements
  dynamic "parameter" {
    for_each = var.parameters
    content {
      name  = parameter.value.name
      value = parameter.value.value
    }
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-redis-params"
    }
  )
}

# Redis Replication Group (supports both single node and cluster mode)
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${var.cluster_name}-redis"
  description          = "Redis cache for ${var.cluster_name} application"

  engine               = "redis"
  engine_version       = var.redis_version
  node_type            = var.node_type
  num_cache_clusters   = var.num_cache_nodes
  port                 = 6379
  parameter_group_name = aws_elasticache_parameter_group.redis.name
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [var.security_group_id]

  # Automatic failover must be enabled for multi-AZ
  automatic_failover_enabled = var.num_cache_nodes > 1 ? true : false
  multi_az_enabled           = var.multi_az_enabled

  # Backup and maintenance
  snapshot_retention_limit   = var.snapshot_retention_limit
  snapshot_window            = var.snapshot_window
  maintenance_window         = var.maintenance_window
  auto_minor_version_upgrade = var.auto_minor_version_upgrade

  # Encryption
  at_rest_encryption_enabled = var.at_rest_encryption_enabled
  transit_encryption_enabled = var.transit_encryption_enabled
  auth_token                 = var.auth_token_enabled ? var.auth_token : null

  # Logging
  dynamic "log_delivery_configuration" {
    for_each = var.enable_cloudwatch_logs ? [1] : []
    content {
      destination      = aws_cloudwatch_log_group.redis[0].name
      destination_type = "cloudwatch-logs"
      log_format       = "json"
      log_type         = "slow-log"
    }
  }

  dynamic "log_delivery_configuration" {
    for_each = var.enable_cloudwatch_logs ? [1] : []
    content {
      destination      = aws_cloudwatch_log_group.redis[0].name
      destination_type = "cloudwatch-logs"
      log_format       = "json"
      log_type         = "engine-log"
    }
  }

  # Notification topic for events (optional)
  notification_topic_arn = var.notification_topic_arn

  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-redis"
    }
  )
}

# CloudWatch Log Group for Redis logs
resource "aws_cloudwatch_log_group" "redis" {
  count             = var.enable_cloudwatch_logs ? 1 : 0
  name              = "/aws/elasticache/${var.cluster_name}-redis"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-redis-logs"
    }
  )
}

# CloudWatch alarms for monitoring
resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  count               = var.enable_alarms ? 1 : 0
  alarm_name          = "${var.cluster_name}-redis-cpu-utilization"
  alarm_description   = "Redis CPU utilization is too high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = var.cpu_threshold
  treat_missing_data  = "notBreaching"

  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.redis.id
  }

  alarm_actions = var.alarm_actions

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "redis_memory" {
  count               = var.enable_alarms ? 1 : 0
  alarm_name          = "${var.cluster_name}-redis-memory-utilization"
  alarm_description   = "Redis memory utilization is too high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = var.memory_threshold
  treat_missing_data  = "notBreaching"

  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.redis.id
  }

  alarm_actions = var.alarm_actions

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "redis_evictions" {
  count               = var.enable_alarms ? 1 : 0
  alarm_name          = "${var.cluster_name}-redis-evictions"
  alarm_description   = "Redis evictions are too high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Evictions"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = var.evictions_threshold
  treat_missing_data  = "notBreaching"

  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.redis.id
  }

  alarm_actions = var.alarm_actions

  tags = var.tags
}
