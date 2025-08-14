# Lambda function for batch processing
resource "aws_lambda_function" "batch_processor" {
  filename         = "batch_processor.zip"
  function_name    = "${local.name_prefix}-batch-processor"
  role            = aws_iam_role.lambda_batch_processor.arn
  handler         = "index.handler"
  runtime         = var.lambda_runtime
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      RDS_ENDPOINT    = aws_db_instance.main.endpoint
      RDS_PORT        = aws_db_instance.main.port
      DB_NAME         = aws_db_instance.main.db_name
      DB_USERNAME     = aws_db_instance.main.username
      SECRET_ARN      = aws_db_instance.main.master_user_secret[0].secret_arn
      S3_BUCKET       = aws_s3_bucket.app_data.bucket
      SQS_QUEUE_URL   = aws_sqs_queue.main.url
      SQS_DLQ_URL     = aws_sqs_queue.dlq.url
    }
  }

  depends_on = [
    data.archive_file.batch_processor_zip,
    aws_cloudwatch_log_group.lambda_batch_processor,
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-batch-processor"
    Type = "batch-processing"
  })
}

# Lambda function for data transformation
resource "aws_lambda_function" "data_transformer" {
  filename         = "data_transformer.zip"
  function_name    = "${local.name_prefix}-data-transformer"
  role            = aws_iam_role.lambda_data_transformer.arn
  handler         = "index.handler"
  runtime         = var.lambda_runtime
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      RDS_ENDPOINT  = aws_db_instance.main.endpoint
      RDS_PORT      = aws_db_instance.main.port
      DB_NAME       = aws_db_instance.main.db_name
      DB_USERNAME   = aws_db_instance.main.username
      SECRET_ARN    = aws_db_instance.main.master_user_secret[0].secret_arn
      S3_BUCKET     = aws_s3_bucket.app_data.bucket
    }
  }

  depends_on = [
    data.archive_file.data_transformer_zip,
    aws_cloudwatch_log_group.lambda_data_transformer,
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-data-transformer"
    Type = "data-processing"
  })
}

# Lambda function for scheduled tasks
resource "aws_lambda_function" "scheduler" {
  filename         = "scheduler.zip"
  function_name    = "${local.name_prefix}-scheduler"
  role            = aws_iam_role.lambda_scheduler.arn
  handler         = "index.handler"
  runtime         = var.lambda_runtime
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      RDS_ENDPOINT    = aws_db_instance.main.endpoint
      RDS_PORT        = aws_db_instance.main.port
      DB_NAME         = aws_db_instance.main.db_name
      DB_USERNAME     = aws_db_instance.main.username
      SECRET_ARN      = aws_db_instance.main.master_user_secret[0].secret_arn
      SQS_QUEUE_URL   = aws_sqs_queue.main.url
    }
  }

  depends_on = [
    data.archive_file.scheduler_zip,
    aws_cloudwatch_log_group.lambda_scheduler,
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-scheduler"
    Type = "scheduled-tasks"
  })
}

# Lambda function code archives
data "archive_file" "batch_processor_zip" {
  type        = "zip"
  output_path = "batch_processor.zip"
  source {
    content = templatefile("${path.module}/lambda/batch_processor.py", {
      # Template variables can be added here
    })
    filename = "index.py"
  }
  source {
    content  = file("${path.module}/lambda/requirements.txt")
    filename = "requirements.txt"
  }
}

data "archive_file" "data_transformer_zip" {
  type        = "zip"
  output_path = "data_transformer.zip"
  source {
    content = templatefile("${path.module}/lambda/data_transformer.py", {
      # Template variables can be added here
    })
    filename = "index.py"
  }
  source {
    content  = file("${path.module}/lambda/requirements.txt")
    filename = "requirements.txt"
  }
}

data "archive_file" "scheduler_zip" {
  type        = "zip"
  output_path = "scheduler.zip"
  source {
    content = templatefile("${path.module}/lambda/scheduler.py", {
      # Template variables can be added here
    })
    filename = "index.py"
  }
  source {
    content  = file("${path.module}/lambda/requirements.txt")
    filename = "requirements.txt"
  }
}

# Lambda permissions for S3
resource "aws_lambda_permission" "s3_invoke" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.batch_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.app_data.arn
}

# Lambda permissions for SQS
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.main.arn
  function_name    = aws_lambda_function.data_transformer.arn
  batch_size       = 10
  maximum_batching_window_in_seconds = 5

  scaling_config {
    maximum_concurrency = 10
  }
}

# EventBridge rule for scheduled Lambda
resource "aws_cloudwatch_event_rule" "lambda_schedule" {
  name                = "${local.name_prefix}-lambda-schedule"
  description         = "Trigger Lambda function on schedule"
  schedule_expression = "rate(1 hour)"  # Run every hour

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-lambda-schedule"
  })
}

resource "aws_cloudwatch_event_target" "lambda_scheduler" {
  rule      = aws_cloudwatch_event_rule.lambda_schedule.name
  target_id = "LambdaTarget"
  arn       = aws_lambda_function.scheduler.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scheduler.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.lambda_schedule.arn
}

# CloudWatch Log Groups for Lambda functions
resource "aws_cloudwatch_log_group" "lambda_batch_processor" {
  name              = "/aws/lambda/${local.name_prefix}-batch-processor"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-batch-processor-logs"
  })
}

resource "aws_cloudwatch_log_group" "lambda_data_transformer" {
  name              = "/aws/lambda/${local.name_prefix}-data-transformer"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-data-transformer-logs"
  })
}

resource "aws_cloudwatch_log_group" "lambda_scheduler" {
  name              = "/aws/lambda/${local.name_prefix}-scheduler"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-scheduler-logs"
  })
}

# IAM roles for Lambda functions
# Batch Processor Role
resource "aws_iam_role" "lambda_batch_processor" {
  name = "${local.name_prefix}-lambda-batch-processor-role"

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

resource "aws_iam_role_policy_attachment" "lambda_batch_processor_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
  role       = aws_iam_role.lambda_batch_processor.name
}

resource "aws_iam_role_policy" "lambda_batch_processor" {
  name = "${local.name_prefix}-lambda-batch-processor-policy"
  role = aws_iam_role.lambda_batch_processor.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.app_data.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.app_data.arn
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          aws_sqs_queue.main.arn,
          aws_sqs_queue.dlq.arn
        ]
      },
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
        Resource = [
          aws_kms_key.rds.arn,
          aws_kms_key.s3.arn,
          aws_kms_key.sqs.arn
        ]
      }
    ]
  })
}

# Data Transformer Role
resource "aws_iam_role" "lambda_data_transformer" {
  name = "${local.name_prefix}-lambda-data-transformer-role"

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

resource "aws_iam_role_policy_attachment" "lambda_data_transformer_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
  role       = aws_iam_role.lambda_data_transformer.name
}

resource "aws_iam_role_policy" "lambda_data_transformer" {
  name = "${local.name_prefix}-lambda-data-transformer-policy"
  role = aws_iam_role.lambda_data_transformer.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.main.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.app_data.arn}/*"
      },
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
        Resource = [
          aws_kms_key.rds.arn,
          aws_kms_key.s3.arn,
          aws_kms_key.sqs.arn
        ]
      }
    ]
  })
}

# Scheduler Role
resource "aws_iam_role" "lambda_scheduler" {
  name = "${local.name_prefix}-lambda-scheduler-role"

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

resource "aws_iam_role_policy_attachment" "lambda_scheduler_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
  role       = aws_iam_role.lambda_scheduler.name
}

resource "aws_iam_role_policy" "lambda_scheduler" {
  name = "${local.name_prefix}-lambda-scheduler-policy"
  role = aws_iam_role.lambda_scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.main.arn
      },
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
        Resource = [
          aws_kms_key.rds.arn,
          aws_kms_key.sqs.arn
        ]
      }
    ]
  })
}

# Lambda layers for common dependencies
resource "aws_lambda_layer_version" "python_dependencies" {
  filename            = "python_dependencies.zip"
  layer_name          = "${local.name_prefix}-python-dependencies"
  compatible_runtimes = ["python3.11"]
  description         = "Common Python dependencies for ${local.name_prefix}"

  depends_on = [data.archive_file.python_dependencies_zip]
}

data "archive_file" "python_dependencies_zip" {
  type        = "zip"
  output_path = "python_dependencies.zip"
  source_dir  = "${path.module}/lambda/layers/python"
}

# Dead Letter Queue configuration for Lambda functions
resource "aws_lambda_function_event_invoke_config" "batch_processor" {
  function_name = aws_lambda_function.batch_processor.function_name

  destination_config {
    on_failure {
      destination = aws_sqs_queue.dlq.arn
    }
  }

  maximum_retry_attempts = 2
}

resource "aws_lambda_function_event_invoke_config" "data_transformer" {
  function_name = aws_lambda_function.data_transformer.function_name

  destination_config {
    on_failure {
      destination = aws_sqs_queue.dlq.arn
    }
  }

  maximum_retry_attempts = 2
}

resource "aws_lambda_function_event_invoke_config" "scheduler" {
  function_name = aws_lambda_function.scheduler.function_name

  destination_config {
    on_failure {
      destination = aws_sqs_queue.dlq.arn
    }
  }

  maximum_retry_attempts = 2
}
