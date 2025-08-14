# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnet-group"
  subnet_ids = aws_subnet.database[*].id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-db-subnet-group"
  })
}

# DB Parameter Group for PostGIS
resource "aws_db_parameter_group" "postgres_postgis" {
  family = "postgres15"
  name   = "${local.name_prefix}-postgres-postgis"

  parameter {
    name  = "shared_preload_libraries"
    value = "postgis"
  }

  parameter {
    name  = "log_statement"
    value = "all"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-postgres-postgis-params"
  })
}

# RDS Instance
resource "aws_db_instance" "main" {
  identifier = "${local.name_prefix}-postgres"

  # Engine configuration
  engine         = "postgres"
  engine_version = var.rds_engine_version
  instance_class = var.rds_instance_class

  # Storage configuration
  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = var.rds_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id           = aws_kms_key.rds.arn

  # Database configuration
  db_name  = var.rds_database_name
  username = var.rds_username
  manage_master_user_password = true
  master_user_secret_kms_key_id = aws_kms_key.rds.arn

  # Network configuration
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  port                   = 5432

  # Backup configuration
  backup_retention_period = var.rds_backup_retention_period
  backup_window          = var.rds_backup_window
  maintenance_window     = var.rds_maintenance_window
  copy_tags_to_snapshot  = true
  skip_final_snapshot    = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "${local.name_prefix}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  # Monitoring and logging
  monitoring_interval             = var.enable_detailed_monitoring ? 60 : 0
  monitoring_role_arn            = var.enable_detailed_monitoring ? aws_iam_role.rds_monitoring[0].arn : null
  performance_insights_enabled   = var.environment == "prod"
  performance_insights_kms_key_id = var.environment == "prod" ? aws_kms_key.rds.arn : null
  performance_insights_retention_period = var.environment == "prod" ? 7 : null
  
  enabled_cloudwatch_logs_exports = ["postgresql"]

  # Security
  deletion_protection = var.rds_deletion_protection
  parameter_group_name = aws_db_parameter_group.postgres_postgis.name

  # Auto minor version upgrade
  auto_minor_version_upgrade = var.environment != "prod"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-postgres"
  })

  depends_on = [
    aws_cloudwatch_log_group.rds
  ]
}

# RDS Monitoring Role
resource "aws_iam_role" "rds_monitoring" {
  count = var.enable_detailed_monitoring ? 1 : 0
  name  = "${local.name_prefix}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  count      = var.enable_detailed_monitoring ? 1 : 0
  role       = aws_iam_role.rds_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# CloudWatch Log Group for RDS
resource "aws_cloudwatch_log_group" "rds" {
  name              = "/aws/rds/instance/${local.name_prefix}-postgres/postgresql"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-rds-logs"
  })
}

# Read Replica (for production)
resource "aws_db_instance" "read_replica" {
  count = var.environment == "prod" ? 1 : 0

  identifier             = "${local.name_prefix}-postgres-read-replica"
  replicate_source_db    = aws_db_instance.main.identifier
  instance_class         = var.rds_instance_class
  publicly_accessible    = false
  auto_minor_version_upgrade = false
  
  # Monitoring
  monitoring_interval = var.enable_detailed_monitoring ? 60 : 0
  monitoring_role_arn = var.enable_detailed_monitoring ? aws_iam_role.rds_monitoring[0].arn : null
  performance_insights_enabled = true
  performance_insights_kms_key_id = aws_kms_key.rds.arn

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-postgres-read-replica"
    Type = "read-replica"
  })
}

# Database initialization Lambda function
resource "aws_lambda_function" "db_init" {
  filename         = "db_init.zip"
  function_name    = "${local.name_prefix}-db-init"
  role            = aws_iam_role.lambda_db_init.arn
  handler         = "index.handler"
  runtime         = "python3.11"
  timeout         = 300
  memory_size     = 256

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      RDS_ENDPOINT = aws_db_instance.main.endpoint
      RDS_PORT     = aws_db_instance.main.port
      DB_NAME      = aws_db_instance.main.db_name
      DB_USERNAME  = aws_db_instance.main.username
      SECRET_ARN   = aws_db_instance.main.master_user_secret[0].secret_arn
    }
  }

  depends_on = [
    data.archive_file.db_init_zip,
    aws_cloudwatch_log_group.lambda_db_init,
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-db-init"
  })
}

# Lambda function code for DB initialization
data "archive_file" "db_init_zip" {
  type        = "zip"
  output_path = "db_init.zip"
  source {
    content = templatefile("${path.module}/lambda/db_init.py", {
      sql_file_content = file("${path.module}/sql/init.sql")
    })
    filename = "index.py"
  }
}

# IAM role for DB init Lambda
resource "aws_iam_role" "lambda_db_init" {
  name = "${local.name_prefix}-lambda-db-init-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_db_init_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
  role       = aws_iam_role.lambda_db_init.name
}

resource "aws_iam_role_policy" "lambda_db_init_secrets" {
  name = "${local.name_prefix}-lambda-db-init-secrets"
  role = aws_iam_role.lambda_db_init.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_db_instance.main.master_user_secret[0].secret_arn
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = aws_kms_key.rds.arn
      }
    ]
  })
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_db_init" {
  name              = "/aws/lambda/${local.name_prefix}-db-init"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-lambda-db-init-logs"
  })
}

# Invoke the Lambda function to initialize the database
resource "aws_lambda_invocation" "db_init" {
  function_name = aws_lambda_function.db_init.function_name

  input = jsonencode({
    action = "initialize"
  })

  depends_on = [
    aws_db_instance.main
  ]
}
