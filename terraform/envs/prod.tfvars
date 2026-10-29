# Ambiente de produção (único).
environment = "prod"
region      = "us-east-1"

# RDS PostgreSQL 15+ (pgvector) — comece pequeno; suba a classe se a carga exigir.
rds_instance_class      = "db.t4g.micro"
rds_engine_version      = "15.19"
rds_allocated_storage   = 20
rds_multi_az            = false
rds_backup_retention    = 7
rds_deletion_protection = true

# ElastiCache Redis 7 (broker Celery + rate limit).
redis_node_type      = "cache.t3.micro"
redis_engine_version = "7.1"
# redis_auth_token = "troque-por-um-token-forte"   # habilita AUTH + TLS in-transit

# ECS Fargate.
api_cpu              = 512
api_memory           = 1024
worker_cpu           = 512
worker_memory        = 1024
api_desired_count    = 1
worker_desired_count = 1
api_min_count        = 1
api_max_count        = 4
worker_min_count     = 1
worker_max_count     = 2

# LLM/RAG.
openai_base_url = "https://spillway.ensinoeinstein.com/openai/v1"
allowed_models  = ["azure/gpt-5-mini", "azure/gpt-6-luna"]
# openai_api_key  = "coloque aqui ou via TF_VAR_openai_api_key (nunca versionar)"