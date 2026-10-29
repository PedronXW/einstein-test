variable "region" {
  description = "Região AWS."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Prefixo usado nos nomes de recursos (bootstrap)."
  type        = string
  default     = "einstein"
}

variable "environment" {
  description = "Ambiente (bootstrap)."
  type        = string
  default     = "prod"
}

variable "github_repo" {
  description = "Repositório GitHub no formato owner/repo — subject do trust policy."
  type        = string
  default     = "PedronXW/einstein-test"
}