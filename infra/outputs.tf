# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "database_subnet_ids" {
  description = "IDs of the database subnets"
  value       = aws_subnet.database[*].id
}

# Security Group Outputs
output "alb_security_group_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb.id
}

output "ecs_security_group_id" {
  description = "ID of the ECS security group"
  value       = aws_security_group.ecs.id
}

output "rds_security_group_id" {
  description = "ID of the RDS security group"
  value       = aws_security_group.rds.id
}

output "lambda_security_group_id" {
  description = "ID of the Lambda security group"
  value       = aws_security_group.lambda.id
}

# RDS Outputs
output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "rds_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_db_instance.main.db_name
}

output "rds_username" {
  description = "RDS master username"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "rds_secret_arn" {
  description = "ARN of the RDS master password secret"
  value       = aws_db_instance.main.master_user_secret[0].secret_arn
  sensitive   = true
}

output "rds_read_replica_endpoint" {
  description = "RDS read replica endpoint"
  value       = var.environment == "prod" ? aws_db_instance.read_replica[0].endpoint : null
  sensitive   = true
}

# ECS Outputs
output "ecs_cluster_id" {
  description = "ID of the ECS cluster"
  value       = aws_ecs_cluster.main.id
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.app.name
}

output "ecs_task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = aws_ecs_task_definition.app.arn
}

# ALB Outputs
output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.main.zone_id
}

output "alb_arn" {
  description = "ARN of the load balancer"
  value       = aws_lb.main.arn
}

output "alb_target_group_arn" {
  description = "ARN of the ALB target group"
  value       = aws_lb_target_group.app.arn
}

# S3 Outputs
output "s3_app_data_bucket" {
  description = "Name of the S3 bucket for application data"
  value       = aws_s3_bucket.app_data.bucket
}

output "s3_app_data_bucket_arn" {
  description = "ARN of the S3 bucket for application data"
  value       = aws_s3_bucket.app_data.arn
}

output "s3_static_assets_bucket" {
  description = "Name of the S3 bucket for static assets"
  value       = aws_s3_bucket.static_assets.bucket
}

output "s3_static_assets_bucket_arn" {
  description = "ARN of the S3 bucket for static assets"
  value       = aws_s3_bucket.static_assets.arn
}

output "s3_logs_bucket" {
  description = "Name of the S3 bucket for logs"
  value       = aws_s3_bucket.logs.bucket
}

output "s3_lambda_artifacts_bucket" {
  description = "Name of the S3 bucket for Lambda artifacts"
  value       = aws_s3_bucket.lambda_artifacts.bucket
}

# Lambda Outputs
output "lambda_batch_processor_arn" {
  description = "ARN of the batch processor Lambda function"
  value       = aws_lambda_function.batch_processor.arn
}

output "lambda_data_transformer_arn" {
  description = "ARN of the data transformer Lambda function"
  value       = aws_lambda_function.data_transformer.arn
}

output "lambda_scheduler_arn" {
  description = "ARN of the scheduler Lambda function"
  value       = aws_lambda_function.scheduler.arn
}

output "lambda_db_init_arn" {
  description = "ARN of the database initialization Lambda function"
  value       = aws_lambda_function.db_init.arn
}

# CloudFront Outputs
output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.main.id
}

output "cloudfront_distribution_arn" {
  description = "ARN of the CloudFront distribution"
  value       = aws_cloudfront_distribution.main.arn
}

output "cloudfront_domain_name" {
  description = "Domain name of the CloudFront distribution"
  value       = aws_cloudfront_distribution.main.domain_name
}

output "cloudfront_hosted_zone_id" {
  description = "Hosted zone ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.main.hosted_zone_id
}

# SQS Outputs
output "sqs_main_queue_url" {
  description = "URL of the main SQS queue"
  value       = aws_sqs_queue.main.url
}

output "sqs_main_queue_arn" {
  description = "ARN of the main SQS queue"
  value       = aws_sqs_queue.main.arn
}

output "sqs_dlq_url" {
  description = "URL of the dead letter queue"
  value       = aws_sqs_queue.dlq.url
}

output "sqs_high_priority_queue_url" {
  description = "URL of the high priority SQS queue"
  value       = aws_sqs_queue.high_priority.url
}

output "sqs_batch_processing_queue_url" {
  description = "URL of the batch processing SQS queue"
  value       = aws_sqs_queue.batch_processing.url
}

output "sqs_fifo_queue_url" {
  description = "URL of the FIFO SQS queue"
  value       = aws_sqs_queue.fifo.url
}

output "sqs_notifications_queue_url" {
  description = "URL of the notifications SQS queue"
  value       = aws_sqs_queue.notifications.url
}

# Secrets Manager Outputs
output "app_secrets_arn" {
  description = "ARN of the application secrets"
  value       = aws_secretsmanager_secret.app_secrets.arn
  sensitive   = true
}

output "db_connection_secret_arn" {
  description = "ARN of the database connection secret"
  value       = aws_secretsmanager_secret.db_connection.arn
  sensitive   = true
}

output "third_party_apis_secret_arn" {
  description = "ARN of the third-party APIs secret"
  value       = aws_secretsmanager_secret.third_party_apis.arn
  sensitive   = true
}

# KMS Key Outputs
output "kms_rds_key_id" {
  description = "ID of the RDS KMS key"
  value       = aws_kms_key.rds.key_id
}

output "kms_s3_key_id" {
  description = "ID of the S3 KMS key"
  value       = aws_kms_key.s3.key_id
}

output "kms_secrets_key_id" {
  description = "ID of the Secrets Manager KMS key"
  value       = aws_kms_key.secrets.key_id
}

output "kms_cloudwatch_key_id" {
  description = "ID of the CloudWatch KMS key"
  value       = aws_kms_key.cloudwatch.key_id
}

output "kms_ecs_key_id" {
  description = "ID of the ECS KMS key"
  value       = aws_kms_key.ecs.key_id
}

output "kms_sqs_key_id" {
  description = "ID of the SQS KMS key"
  value       = aws_kms_key.sqs.key_id
}

# IAM Role Outputs
output "ecs_task_role_arn" {
  description = "ARN of the ECS task role"
  value       = aws_iam_role.ecs_task.arn
}

output "ecs_execution_role_arn" {
  description = "ARN of the ECS execution role"
  value       = aws_iam_role.ecs_execution.arn
}

output "lambda_batch_processor_role_arn" {
  description = "ARN of the Lambda batch processor role"
  value       = aws_iam_role.lambda_batch_processor.arn
}

output "github_actions_role_arn" {
  description = "ARN of the GitHub Actions role"
  value       = aws_iam_role.github_actions.arn
}

# SNS Outputs
output "alerts_topic_arn" {
  description = "ARN of the alerts SNS topic"
  value       = aws_sns_topic.alerts.arn
}

# Service Discovery Outputs
output "service_discovery_namespace_id" {
  description = "ID of the service discovery namespace"
  value       = aws_service_discovery_private_dns_namespace.main.id
}

output "service_discovery_service_id" {
  description = "ID of the service discovery service"
  value       = aws_service_discovery_service.app.id
}

# WAF Outputs
output "waf_web_acl_id" {
  description = "ID of the WAF web ACL"
  value       = var.enable_waf ? aws_wafv2_web_acl.main[0].id : null
}

output "waf_web_acl_arn" {
  description = "ARN of the WAF web ACL"
  value       = var.enable_waf ? aws_wafv2_web_acl.main[0].arn : null
}

# Route53 Outputs
output "domain_name" {
  description = "Domain name (if configured)"
  value       = var.domain_name
}

output "route53_zone_id" {
  description = "Route53 hosted zone ID (if domain configured)"
  value       = var.domain_name != "" ? data.aws_route53_zone.main[0].zone_id : null
}

# Environment Information
output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "project_name" {
  description = "Project name"
  value       = var.project_name
}

output "aws_region" {
  description = "AWS region"
  value       = data.aws_region.current.name
}

output "aws_account_id" {
  description = "AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}

# Application URLs
output "application_url" {
  description = "Application URL"
  value = var.domain_name != "" ? (
    var.certificate_arn != "" ? "https://${var.domain_name}" : "http://${var.domain_name}"
  ) : (
    var.certificate_arn != "" ? "https://${aws_lb.main.dns_name}" : "http://${aws_lb.main.dns_name}"
  )
}

output "cloudfront_url" {
  description = "CloudFront distribution URL"
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}

# Health Check URL
output "health_check_url" {
  description = "Health check URL"
  value = var.certificate_arn != "" ? (
    "https://${aws_lb.main.dns_name}/health"
  ) : (
    "http://${aws_lb.main.dns_name}/health"
  )
}

# Connection Information
output "database_connection_info" {
  description = "Database connection information"
  value = {
    endpoint = aws_db_instance.main.endpoint
    port     = aws_db_instance.main.port
    database = aws_db_instance.main.db_name
    username = aws_db_instance.main.username
    # Note: Password is stored in Secrets Manager
    secret_arn = aws_db_instance.main.master_user_secret[0].secret_arn
  }
  sensitive = true
}

# Monitoring Dashboard URL
output "cloudwatch_dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = "https://${data.aws_region.current.name}.console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:"
}

# Log Groups
output "log_groups" {
  description = "CloudWatch log groups"
  value = {
    ecs_app               = aws_cloudwatch_log_group.app.name
    lambda_batch_processor = aws_cloudwatch_log_group.lambda_batch_processor.name
    lambda_data_transformer = aws_cloudwatch_log_group.lambda_data_transformer.name
    lambda_scheduler      = aws_cloudwatch_log_group.lambda_scheduler.name
    lambda_db_init       = aws_cloudwatch_log_group.lambda_db_init.name
    rds                  = aws_cloudwatch_log_group.rds.name
  }
}
