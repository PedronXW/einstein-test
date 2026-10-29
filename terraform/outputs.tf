output "alb_dns_name" {
  description = "DNS público do ALB (endpoint da API)."
  value       = aws_lb.main.dns_name
}

output "ecr_repository_url" {
  description = "URL do repositório ECR (exportar como secret no GitHub se necessário)."
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  description = "Nome do cluster ECS."
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_api" {
  description = "Nome do serviço ECS da API."
  value       = aws_ecs_service.api.name
}

output "ecs_service_worker" {
  description = "Nome do serviço ECS do worker."
  value       = aws_ecs_service.worker.name
}

output "rds_address" {
  description = "Endpoint do PostgreSQL."
  value       = aws_db_instance.postgres.address
}

output "redis_endpoint" {
  description = "Endpoint do ElastiCache Redis."
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "s3_bucket" {
  description = "Bucket S3 dos arquivos."
  value       = aws_s3_bucket.files.bucket
}

output "secrets_app_arn" {
  description = "ARN do secret da aplicação."
  value       = aws_secretsmanager_secret.app.arn
}

output "ecs_execution_role_arn" {
  description = "ARN da execution role do ECS."
  value       = aws_iam_role.ecs_execution.arn
}

output "ecs_task_role_arn" {
  description = "ARN da task role do ECS."
  value       = aws_iam_role.ecs_task.arn
}