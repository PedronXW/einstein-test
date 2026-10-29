resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.name}-redis"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = local.name
  description                = "${local.name} redis (broker celery + rate limit)"
  engine                     = "redis"
  engine_version             = var.redis_engine_version
  node_type                  = var.redis_node_type
  num_cache_clusters         = 1
  port                       = 6379
  parameter_group_name       = "default.redis7"
  subnet_group_name          = aws_elasticache_subnet_group.redis.name
  security_group_ids         = [aws_security_group.redis.id]
  automatic_failover_enabled = false
  multi_az_enabled           = false
  auth_token                 = var.redis_auth_token != "" ? var.redis_auth_token : null
  transit_encryption_enabled = var.redis_auth_token != ""
  at_rest_encryption_enabled = true
  snapshot_retention_limit   = 2
  snapshot_window            = "02:00-03:00"
  maintenance_window         = "sun:03:00-sun:04:00"
  apply_immediately          = false

  tags = { Name = "${local.name}-redis" }
}