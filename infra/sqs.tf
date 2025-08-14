# Main SQS Queue for processing tasks
resource "aws_sqs_queue" "main" {
  name                       = "${local.name_prefix}-main-queue"
  visibility_timeout_seconds = var.sqs_visibility_timeout_seconds
  message_retention_seconds  = var.sqs_message_retention_seconds
  max_message_size          = 262144  # 256 KB
  delay_seconds             = 0
  receive_wait_time_seconds = 10  # Long polling

  # Dead Letter Queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.sqs_max_receive_count
  })

  # Server-side encryption
  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-main-queue"
    Type = "processing"
  })
}

# Dead Letter Queue
resource "aws_sqs_queue" "dlq" {
  name                       = "${local.name_prefix}-dlq"
  visibility_timeout_seconds = var.sqs_visibility_timeout_seconds
  message_retention_seconds  = 1209600  # 14 days (maximum)
  max_message_size          = 262144   # 256 KB

  # Server-side encryption
  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-dlq"
    Type = "dead-letter"
  })
}

# High-priority queue for urgent tasks
resource "aws_sqs_queue" "high_priority" {
  name                       = "${local.name_prefix}-high-priority-queue"
  visibility_timeout_seconds = var.sqs_visibility_timeout_seconds
  message_retention_seconds  = var.sqs_message_retention_seconds
  max_message_size          = 262144
  delay_seconds             = 0
  receive_wait_time_seconds = 5  # Faster polling for high priority

  # Dead Letter Queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.sqs_max_receive_count
  })

  # Server-side encryption
  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-high-priority-queue"
    Type = "high-priority"
  })
}

# Batch processing queue for large datasets
resource "aws_sqs_queue" "batch_processing" {
  name                       = "${local.name_prefix}-batch-processing-queue"
  visibility_timeout_seconds = 900  # 15 minutes for batch processing
  message_retention_seconds  = var.sqs_message_retention_seconds
  max_message_size          = 262144
  delay_seconds             = 0
  receive_wait_time_seconds = 20  # Longer polling for batch processing

  # Dead Letter Queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 2  # Fewer retries for batch processing
  })

  # Server-side encryption
  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-batch-processing-queue"
    Type = "batch-processing"
  })
}

# FIFO queue for ordered processing
resource "aws_sqs_queue" "fifo" {
  name                        = "${local.name_prefix}-fifo-queue.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  visibility_timeout_seconds  = var.sqs_visibility_timeout_seconds
  message_retention_seconds   = var.sqs_message_retention_seconds
  max_message_size           = 262144
  delay_seconds              = 0
  receive_wait_time_seconds  = 10

  # Dead Letter Queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.fifo_dlq.arn
    maxReceiveCount     = var.sqs_max_receive_count
  })

  # Server-side encryption
  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-fifo-queue"
    Type = "fifo"
  })
}

# FIFO Dead Letter Queue
resource "aws_sqs_queue" "fifo_dlq" {
  name                        = "${local.name_prefix}-fifo-dlq.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  visibility_timeout_seconds  = var.sqs_visibility_timeout_seconds
  message_retention_seconds   = 1209600  # 14 days
  max_message_size           = 262144

  # Server-side encryption
  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-fifo-dlq"
    Type = "fifo-dead-letter"
  })
}

# Notification queue for alerts and notifications
resource "aws_sqs_queue" "notifications" {
  name                       = "${local.name_prefix}-notifications-queue"
  visibility_timeout_seconds = 30  # Short timeout for notifications
  message_retention_seconds  = 604800  # 7 days
  max_message_size          = 262144
  delay_seconds             = 0
  receive_wait_time_seconds = 5

  # Dead Letter Queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 5  # More retries for notifications
  })

  # Server-side encryption
  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-notifications-queue"
    Type = "notifications"
  })
}

# SQS Queue Policies
resource "aws_sqs_queue_policy" "main" {
  queue_url = aws_sqs_queue.main.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = [
            aws_iam_role.ecs_task.arn,
            aws_iam_role.lambda_batch_processor.arn,
            aws_iam_role.lambda_data_transformer.arn,
            aws_iam_role.lambda_scheduler.arn
          ]
        }
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.main.arn
      },
      {
        Effect = "Deny"
        Principal = "*"
        Action = "sqs:*"
        Resource = aws_sqs_queue.main.arn
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

resource "aws_sqs_queue_policy" "high_priority" {
  queue_url = aws_sqs_queue.high_priority.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = [
            aws_iam_role.ecs_task.arn,
            aws_iam_role.lambda_batch_processor.arn,
            aws_iam_role.lambda_data_transformer.arn,
            aws_iam_role.lambda_scheduler.arn
          ]
        }
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.high_priority.arn
      },
      {
        Effect = "Deny"
        Principal = "*"
        Action = "sqs:*"
        Resource = aws_sqs_queue.high_priority.arn
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# CloudWatch Alarms for SQS
resource "aws_cloudwatch_metric_alarm" "sqs_dlq_messages" {
  alarm_name          = "${local.name_prefix}-sqs-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfVisibleMessages"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "5"
  alarm_description   = "This metric monitors messages in the dead letter queue"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "sqs_main_age" {
  alarm_name          = "${local.name_prefix}-sqs-main-message-age"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ApproximateAgeOfOldestMessage"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Maximum"
  threshold           = "900"  # 15 minutes
  alarm_description   = "This metric monitors the age of the oldest message in the main queue"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    QueueName = aws_sqs_queue.main.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "sqs_main_depth" {
  alarm_name          = "${local.name_prefix}-sqs-main-queue-depth"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ApproximateNumberOfVisibleMessages"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "100"
  alarm_description   = "This metric monitors the depth of the main queue"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    QueueName = aws_sqs_queue.main.name
  }

  tags = local.common_tags
}

# SQS Queue redrive policy for testing DLQ reprocessing
resource "aws_sqs_queue_redrive_allow_policy" "dlq" {
  queue_url = aws_sqs_queue.dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue",
    sourceQueueArns   = [
      aws_sqs_queue.main.arn,
      aws_sqs_queue.high_priority.arn,
      aws_sqs_queue.batch_processing.arn,
      aws_sqs_queue.notifications.arn
    ]
  })
}

resource "aws_sqs_queue_redrive_allow_policy" "fifo_dlq" {
  queue_url = aws_sqs_queue.fifo_dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue",
    sourceQueueArns   = [aws_sqs_queue.fifo.arn]
  })
}

# EventBridge rule for SQS monitoring
resource "aws_cloudwatch_event_rule" "sqs_dlq_monitor" {
  name        = "${local.name_prefix}-sqs-dlq-monitor"
  description = "Monitor DLQ for failed messages"

  event_pattern = jsonencode({
    source      = ["aws.sqs"]
    detail-type = ["SQS Queue Message Received"]
    detail = {
      queueName = [aws_sqs_queue.dlq.name]
    }
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-sqs-dlq-monitor"
  })
}

resource "aws_cloudwatch_event_target" "sqs_dlq_notification" {
  rule      = aws_cloudwatch_event_rule.sqs_dlq_monitor.name
  target_id = "SQSDLQNotification"
  arn       = aws_sns_topic.alerts.arn

  input_transformer {
    input_paths = {
      queue = "$.detail.queueName"
      time  = "$.time"
    }
    input_template = "{\"message\": \"Message received in DLQ: <queue> at <time>\"}"
  }
}
