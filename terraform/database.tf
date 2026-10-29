resource "aws_db_subnet_group" "postgres" {
  name       = "${local.name}-rds"
  subnet_ids = aws_subnet.private[*].id

  tags = { Name = "${local.name}-rds" }
}

resource "random_password" "rds" {
  length  = 32
  special = false
}

resource "aws_db_instance" "postgres" {
  identifier                 = local.name
  engine                     = "postgres"
  engine_version             = var.rds_engine_version
  instance_class             = var.rds_instance_class
  allocated_storage          = var.rds_allocated_storage
  storage_type               = "gp3"
  storage_encrypted          = true
  db_name                    = "einstein"
  username                   = "einstein"
  password                   = random_password.rds.result
  db_subnet_group_name       = aws_db_subnet_group.postgres.name
  vpc_security_group_ids     = [aws_security_group.rds.id]
  multi_az                   = var.rds_multi_az
  backup_retention_period    = var.rds_backup_retention
  backup_window              = "03:00-04:00"
  maintenance_window         = "sun:04:30-sun:05:30"
  skip_final_snapshot        = false
  final_snapshot_identifier  = "${local.name}-final"
  deletion_protection        = var.rds_deletion_protection
  apply_immediately          = false
  auto_minor_version_upgrade = true

  # O `alembic upgrade head` (entrypoint) roda `CREATE EXTENSION IF NOT EXISTS
  # vector` na 1ª subida — não é necessário gerenciar a extension aqui.
  tags = { Name = "${local.name}-postgres" }
}