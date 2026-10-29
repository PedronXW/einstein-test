variable "environment" {
  description = "Ambiente-alvo (prod)."
  type        = string
  default     = "prod"
}

variable "project" {
  description = "Prefixo curto usado em recursos com nome global (ex.: bucket S3)."
  type        = string
  default     = "einstein"
}

variable "app_name" {
  description = "Nome da aplicação (tags/nomes de recursos)."
  type        = string
  default     = "einstein-test"
}

variable "region" {
  description = "Região AWS."
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR da VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "vpc_enable_nat" {
  description = "Cria NAT gateway (custo) para subnets privadas; desative para economizar em teste."
  type        = bool
  default     = true
}

variable "rds_instance_class" {
  description = "Classe da instância RDS."
  type        = string
  default     = "db.t4g.micro"
}

variable "rds_engine_version" {
  description = "Versão do PostgreSQL no RDS (>= 15.2 para suportar pgvector)."
  type        = string
  default     = "15.19"
}

variable "rds_allocated_storage" {
  description = "Armazenamento alocado no RDS (GB)."
  type        = number
  default     = 20
}

variable "rds_multi_az" {
  description = "Multi-AZ na instância RDS."
  type        = bool
  default     = false
}

variable "rds_backup_retention" {
  description = "Dias de retenção de backup do RDS."
  type        = number
  default     = 7
}

variable "rds_deletion_protection" {
  description = "Protege a instância RDS contra exclusão acidental."
  type        = bool
  default     = true
}

variable "redis_node_type" {
  description = "Tipo de nó do ElastiCache Redis."
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_engine_version" {
  description = "Versão do Redis no ElastiCache."
  type        = string
  default     = "7.1"
}

variable "redis_auth_token" {
  description = "Token de auth do Redis (AUTH). Vazio = sem auth (rede privada + SG)."
  type        = string
  default     = ""
}

variable "api_cpu" {
  description = "CPU (unidades vCPU*1024) do task def da API."
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "Memória (MB) do task def da API."
  type        = number
  default     = 1024
}

variable "worker_cpu" {
  description = "CPU (unidades vCPU*1024) do task def do worker."
  type        = number
  default     = 512
}

variable "worker_memory" {
  description = "Memória (MB) do task def do worker."
  type        = number
  default     = 1024
}

variable "api_desired_count" {
  description = "Réplicas desejadas da API."
  type        = number
  default     = 1
}

variable "worker_desired_count" {
  description = "Réplicas desejadas do worker."
  type        = number
  default     = 1
}

variable "api_min_count" {
  description = "Mínimo de réplicas da API (autoscaling)."
  type        = number
  default     = 1
}

variable "api_max_count" {
  description = "Máximo de réplicas da API (autoscaling)."
  type        = number
  default     = 4
}

variable "worker_min_count" {
  description = "Mínimo de réplicas do worker (autoscaling)."
  type        = number
  default     = 1
}

variable "worker_max_count" {
  description = "Máximo de réplicas do worker (autoscaling)."
  type        = number
  default     = 2
}

variable "openai_api_key" {
  description = "Chave da API OpenAI-compatível (secreto; passe via TF_VAR_openai_api_key)."
  type        = string
  default     = ""
}

variable "openai_base_url" {
  description = "Base URL da API OpenAI-compatível usada por embedder e chat."
  type        = string
  default     = "https://spillway.ensinoeinstein.com/openai/v1"
}

variable "allowed_models" {
  description = "Modelos de LLM permitidos (comma-separated/lista)."
  type        = list(string)
  default     = ["azure/gpt-5-mini", "azure/gpt-6-luna"]
}

variable "log_retention_days" {
  description = "Retenção dos CloudWatch log groups (dias)."
  type        = number
  default     = 14
}