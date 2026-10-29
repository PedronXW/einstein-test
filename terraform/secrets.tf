resource "random_password" "jwt" {
  length  = 64
  special = false
}

# Secrets agregados da aplicação (lidos via `secrets` no task def, por chave).
resource "aws_secretsmanager_secret" "app" {
  name_prefix = "${var.app_name}/${var.environment}/"

  tags = { Name = "${var.app_name}-${var.environment}-app" }
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id

  secret_string = jsonencode({
    JWT_SECRET            = random_password.jwt.result
    OPENAI_API_KEY        = var.openai_api_key
    DATABASE_URL          = "postgresql://einstein:${urlencode(random_password.rds.result)}@${aws_db_instance.postgres.address}:5432/einstein"
    CELERY_BROKER_URL     = "redis://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379/0"
    CELERY_RESULT_BACKEND = "redis://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379/0"
  })
}