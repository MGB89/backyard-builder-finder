# KMS Keys for encryption

# RDS KMS Key
resource "aws_kms_key" "rds" {
  description             = "KMS key for RDS encryption"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow RDS Service"
        Effect = "Allow"
        Principal = {
          Service = "rds.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-rds-kms"
    Type = "rds-encryption"
  })
}

resource "aws_kms_alias" "rds" {
  name          = "alias/${local.name_prefix}-rds"
  target_key_id = aws_kms_key.rds.key_id
}

# S3 KMS Key
resource "aws_kms_key" "s3" {
  description             = "KMS key for S3 encryption"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow S3 Service"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-s3-kms"
    Type = "s3-encryption"
  })
}

resource "aws_kms_alias" "s3" {
  name          = "alias/${local.name_prefix}-s3"
  target_key_id = aws_kms_key.s3.key_id
}

# Secrets Manager KMS Key
resource "aws_kms_key" "secrets" {
  description             = "KMS key for Secrets Manager"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow Secrets Manager Service"
        Effect = "Allow"
        Principal = {
          Service = "secretsmanager.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-secrets-kms"
    Type = "secrets-encryption"
  })
}

resource "aws_kms_alias" "secrets" {
  name          = "alias/${local.name_prefix}-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}

# CloudWatch Logs KMS Key
resource "aws_kms_key" "cloudwatch" {
  description             = "KMS key for CloudWatch Logs encryption"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow CloudWatch Logs"
        Effect = "Allow"
        Principal = {
          Service = "logs.${data.aws_region.current.name}.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          ArnEquals = {
            "kms:EncryptionContext:aws:logs:arn" = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
          }
        }
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-cloudwatch-kms"
    Type = "cloudwatch-encryption"
  })
}

resource "aws_kms_alias" "cloudwatch" {
  name          = "alias/${local.name_prefix}-cloudwatch"
  target_key_id = aws_kms_key.cloudwatch.key_id
}

# ECS KMS Key
resource "aws_kms_key" "ecs" {
  description             = "KMS key for ECS encryption"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow ECS Service"
        Effect = "Allow"
        Principal = {
          Service = "ecs.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ecs-kms"
    Type = "ecs-encryption"
  })
}

resource "aws_kms_alias" "ecs" {
  name          = "alias/${local.name_prefix}-ecs"
  target_key_id = aws_kms_key.ecs.key_id
}

# SQS KMS Key
resource "aws_kms_key" "sqs" {
  description             = "KMS key for SQS encryption"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow SQS Service"
        Effect = "Allow"
        Principal = {
          Service = "sqs.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-sqs-kms"
    Type = "sqs-encryption"
  })
}

resource "aws_kms_alias" "sqs" {
  name          = "alias/${local.name_prefix}-sqs"
  target_key_id = aws_kms_key.sqs.key_id
}

# SNS KMS Key
resource "aws_kms_key" "sns" {
  description             = "KMS key for SNS encryption"
  deletion_window_in_days = var.environment == "prod" ? 30 : 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow SNS Service"
        Effect = "Allow"
        Principal = {
          Service = "sns.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-sns-kms"
    Type = "sns-encryption"
  })
}

resource "aws_kms_alias" "sns" {
  name          = "alias/${local.name_prefix}-sns"
  target_key_id = aws_kms_key.sns.key_id
}

# Application Secrets
resource "aws_secretsmanager_secret" "app_secrets" {
  name                    = "${local.name_prefix}-app-secrets"
  description             = "Application secrets for ${local.name_prefix}"
  kms_key_id             = aws_kms_key.secrets.arn
  recovery_window_in_days = var.environment == "prod" ? 30 : 0

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-app-secrets"
  })
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    jwt_secret         = random_password.jwt_secret.result
    api_key           = random_password.api_key.result
    encryption_key    = random_password.encryption_key.result
    session_secret    = random_password.session_secret.result
  })
}

# JWT Secret
resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}

# API Key
resource "random_password" "api_key" {
  length  = 32
  special = false
  upper   = true
  lower   = true
  numeric = true
}

# Encryption Key
resource "random_password" "encryption_key" {
  length  = 32
  special = false
  upper   = true
  lower   = true
  numeric = true
}

# Session Secret
resource "random_password" "session_secret" {
  length  = 32
  special = true
}

# Database connection secret for applications
resource "aws_secretsmanager_secret" "db_connection" {
  name                    = "${local.name_prefix}-db-connection"
  description             = "Database connection string for ${local.name_prefix}"
  kms_key_id             = aws_kms_key.secrets.arn
  recovery_window_in_days = var.environment == "prod" ? 30 : 0

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-db-connection"
  })
}

resource "aws_secretsmanager_secret_version" "db_connection" {
  secret_id = aws_secretsmanager_secret.db_connection.id
  secret_string = jsonencode({
    host     = aws_db_instance.main.endpoint
    port     = aws_db_instance.main.port
    database = aws_db_instance.main.db_name
    username = aws_db_instance.main.username
    password = random_password.rds_password.result
    ssl_mode = "require"
    connection_string = "postgresql://${aws_db_instance.main.username}:${random_password.rds_password.result}@${aws_db_instance.main.endpoint}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}?sslmode=require"
  })
}

# Secret for third-party API keys (example)
resource "aws_secretsmanager_secret" "third_party_apis" {
  name                    = "${local.name_prefix}-third-party-apis"
  description             = "Third-party API keys for ${local.name_prefix}"
  kms_key_id             = aws_kms_key.secrets.arn
  recovery_window_in_days = var.environment == "prod" ? 30 : 0

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-third-party-apis"
  })
}

resource "aws_secretsmanager_secret_version" "third_party_apis" {
  secret_id = aws_secretsmanager_secret.third_party_apis.id
  secret_string = jsonencode({
    google_maps_api_key = "CHANGE_ME"
    sendgrid_api_key   = "CHANGE_ME"
    stripe_secret_key  = "CHANGE_ME"
    aws_access_key_id  = "CHANGE_ME"
    aws_secret_access_key = "CHANGE_ME"
  })
}

# Secret rotation for RDS (optional)
resource "aws_secretsmanager_secret_rotation" "rds" {
  count = var.environment == "prod" ? 1 : 0
  
  secret_id           = aws_secretsmanager_secret.rds_password.id
  rotation_lambda_arn = aws_lambda_function.secret_rotation[0].arn

  rotation_rules {
    automatically_after_days = 30
  }
}

# Lambda function for secret rotation
resource "aws_lambda_function" "secret_rotation" {
  count = var.environment == "prod" ? 1 : 0
  
  filename         = "secret_rotation.zip"
  function_name    = "${local.name_prefix}-secret-rotation"
  role            = aws_iam_role.lambda_secret_rotation[0].arn
  handler         = "index.handler"
  runtime         = "python3.11"
  timeout         = 300

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      SECRETS_MANAGER_ENDPOINT = "https://secretsmanager.${data.aws_region.current.name}.amazonaws.com"
    }
  }

  depends_on = [
    data.archive_file.secret_rotation_zip[0],
    aws_cloudwatch_log_group.lambda_secret_rotation[0],
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-secret-rotation"
  })
}

# Lambda function code for secret rotation
data "archive_file" "secret_rotation_zip" {
  count = var.environment == "prod" ? 1 : 0
  
  type        = "zip"
  output_path = "secret_rotation.zip"
  source {
    content = templatefile("${path.module}/lambda/secret_rotation.py", {})
    filename = "index.py"
  }
}

# IAM role for secret rotation Lambda
resource "aws_iam_role" "lambda_secret_rotation" {
  count = var.environment == "prod" ? 1 : 0
  
  name = "${local.name_prefix}-lambda-secret-rotation-role"

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

resource "aws_iam_role_policy_attachment" "lambda_secret_rotation_basic" {
  count = var.environment == "prod" ? 1 : 0
  
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
  role       = aws_iam_role.lambda_secret_rotation[0].name
}

resource "aws_iam_role_policy" "lambda_secret_rotation" {
  count = var.environment == "prod" ? 1 : 0
  
  name = "${local.name_prefix}-lambda-secret-rotation-policy"
  role = aws_iam_role.lambda_secret_rotation[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:DescribeSecret",
          "secretsmanager:GetSecretValue",
          "secretsmanager:PutSecretValue",
          "secretsmanager:UpdateSecretVersionStage"
        ]
        Resource = aws_secretsmanager_secret.rds_password.arn
      },
      {
        Effect = "Allow"
        Action = [
          "rds:ModifyDBInstance"
        ]
        Resource = aws_db_instance.main.arn
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.secrets.arn
      }
    ]
  })
}

# CloudWatch Log Group for secret rotation Lambda
resource "aws_cloudwatch_log_group" "lambda_secret_rotation" {
  count = var.environment == "prod" ? 1 : 0
  
  name              = "/aws/lambda/${local.name_prefix}-secret-rotation"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-secret-rotation-logs"
  })
}

# Lambda permission for Secrets Manager
resource "aws_lambda_permission" "allow_secrets_manager" {
  count = var.environment == "prod" ? 1 : 0
  
  statement_id  = "AllowExecutionFromSecretsManager"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.secret_rotation[0].function_name
  principal     = "secretsmanager.amazonaws.com"
}
