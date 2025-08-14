# Property Assessment System - AWS Infrastructure

This directory contains Terraform configuration for deploying a comprehensive AWS infrastructure for the Property Assessment System. The infrastructure includes all necessary components for a scalable, secure, and highly available property assessment application with PostGIS spatial database capabilities.

## 🏗️ Architecture Overview

The infrastructure consists of the following key components:

- **VPC** with public, private, and database subnets across multiple AZs
- **RDS PostgreSQL** with PostGIS extension for spatial data
- **ECS Fargate** for containerized application hosting
- **Application Load Balancer** with SSL termination
- **CloudFront CDN** for global content delivery
- **S3 buckets** for application data, static assets, and logs
- **Lambda functions** for batch processing and scheduled tasks
- **SQS queues** for asynchronous message processing
- **Secrets Manager** for secure credential storage
- **KMS encryption** for data at rest
- **Comprehensive IAM roles** and security policies

## 📁 File Structure

```
infra/
├── main.tf                    # Main Terraform configuration and providers
├── variables.tf               # Input variables with validation
├── vpc.tf                     # VPC, subnets, NAT gateways, security groups
├── rds.tf                     # PostgreSQL database with PostGIS
├── ecs.tf                     # ECS cluster, services, and task definitions
├── s3.tf                      # S3 buckets with lifecycle policies
├── lambda.tf                  # Lambda functions for batch processing
├── cloudfront.tf              # CloudFront distribution and WAF
├── secrets.tf                 # KMS keys and Secrets Manager
├── iam.tf                     # IAM roles, policies, and OIDC providers
├── alb.tf                     # Application Load Balancer configuration
├── sqs.tf                     # SQS queues and dead letter queues
├── outputs.tf                 # Output values for other systems
├── terraform.tfvars.example   # Example configuration file
├── sql/
│   └── init.sql              # PostgreSQL database initialization
├── lambda/
│   ├── db_init.py            # Database initialization function
│   ├── batch_processor.py    # Batch processing handler
│   ├── data_transformer.py   # Data transformation function
│   ├── scheduler.py          # Scheduled task runner
│   ├── secret_rotation.py    # Secret rotation function
│   ├── requirements.txt      # Python dependencies
│   └── layers/
│       └── python/           # Lambda layer dependencies
├── cloudfront/
│   └── url-rewrite.js        # CloudFront function for SPA routing
└── templates/
    └── maintenance.html      # Maintenance page template
```

## 🚀 Quick Start

### Prerequisites

1. **AWS CLI** configured with appropriate permissions
2. **Terraform** >= 1.0 installed
3. **AWS Account** with necessary service limits
4. **Domain and SSL Certificate** (optional, for custom domain)

### Deployment Steps

1. **Clone and navigate to the infrastructure directory:**
   ```bash
   cd "Property Assessment/infra"
   ```

2. **Copy and customize the variables file:**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your specific values
   ```

3. **Initialize Terraform:**
   ```bash
   terraform init
   ```

4. **Review the deployment plan:**
   ```bash
   terraform plan
   ```

5. **Deploy the infrastructure:**
   ```bash
   terraform apply
   ```

6. **Note the outputs:**
   ```bash
   terraform output
   ```

## ⚙️ Configuration

### Environment-Specific Configuration

The infrastructure supports multiple environments (dev, staging, prod) with different configurations:

#### Development Environment
```hcl
environment = "dev"
rds_instance_class = "db.t3.micro"
ecs_desired_count = 1
s3_force_destroy = true
rds_deletion_protection = false
enable_detailed_monitoring = false
```

#### Production Environment
```hcl
environment = "prod"
rds_instance_class = "db.r5.large"
ecs_desired_count = 3
s3_force_destroy = false
rds_deletion_protection = true
enable_detailed_monitoring = true
enable_waf = true
```

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `aws_region` | AWS region for deployment | `us-west-2` |
| `environment` | Environment name | `dev`, `staging`, `prod` |
| `project_name` | Project identifier | `property-assessment` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `domain_name` | Custom domain name | `""` |
| `certificate_arn` | ACM certificate ARN | `""` |
| `enable_waf` | Enable WAF protection | `false` |
| `allowed_cidr_blocks` | Allowed IP ranges | `["0.0.0.0/0"]` |

## 🔒 Security Features

### Encryption
- **KMS encryption** for all data at rest (RDS, S3, EBS, Secrets Manager)
- **SSL/TLS** encryption for data in transit
- **Separate KMS keys** for different services

### Network Security
- **Private subnets** for application and database tiers
- **Security groups** with least privilege access
- **NAT gateways** for outbound internet access
- **VPC endpoints** for AWS services

### Access Control
- **IAM roles** with minimal required permissions
- **Cross-service roles** for secure service communication
- **Secrets Manager** for credential management
- **Secret rotation** for RDS passwords

### Web Application Security
- **WAF v2** with managed rule sets (optional)
- **CloudFront security headers** policy
- **ALB security groups** restricting access

## 📊 Monitoring and Logging

### CloudWatch Integration
- **Application logs** stored in CloudWatch
- **Custom metrics** for business KPIs
- **Automated alarms** for system health
- **Dashboard** for operational visibility

### Log Management
- **Centralized logging** to S3 with lifecycle policies
- **Structured logging** for applications
- **Audit trails** for all administrative actions
- **Log encryption** with KMS

### Health Checks
- **ALB health checks** for application availability
- **Lambda health monitoring** function
- **Database performance** monitoring
- **SQS queue depth** monitoring

## 🔄 Backup and Disaster Recovery

### Database Backups
- **Automated RDS backups** with point-in-time recovery
- **Cross-region backup** replication (configurable)
- **Read replicas** for production environments
- **Backup encryption** with KMS

### Application Data
- **S3 versioning** enabled for critical buckets
- **Cross-region replication** (configurable)
- **Lifecycle policies** for cost optimization
- **Backup validation** processes

## 📈 Scaling and Performance

### Auto Scaling
- **ECS service auto scaling** based on CPU/memory
- **ALB target group** health monitoring
- **Lambda concurrency** management
- **RDS storage** auto scaling

### Performance Optimization
- **CloudFront CDN** for global content delivery
- **Connection pooling** for database access
- **SQS queues** for asynchronous processing
- **Lambda layers** for code reuse

## 💰 Cost Optimization

### Resource Sizing
- **Environment-specific** instance sizes
- **Spot instances** for non-critical workloads (configurable)
- **Reserved instances** recommendations
- **Storage tiering** with S3 lifecycle policies

### Monitoring
- **Cost allocation tags** on all resources
- **Billing alerts** configuration
- **Resource utilization** monitoring
- **Right-sizing** recommendations

## 🛠️ Operations

### Deployment
- **Blue/green deployments** with ECS
- **Rolling updates** for zero downtime
- **Database migrations** through Lambda
- **Infrastructure as code** with Terraform

### Maintenance
- **Automated patching** for managed services
- **Scheduled maintenance** windows
- **Backup verification** procedures
- **Disaster recovery** testing

### Troubleshooting
- **CloudWatch insights** for log analysis
- **X-Ray tracing** for distributed debugging
- **Performance profiling** tools
- **Health check** endpoints

## 🔧 Customization

### Adding New Services
1. Create new Terraform files for services
2. Update IAM roles and policies
3. Add monitoring and alerting
4. Update documentation

### Environment Variations
1. Create environment-specific variable files
2. Use Terraform workspaces or separate state files
3. Implement environment-specific configurations
4. Test thoroughly before production deployment

## 📚 Additional Resources

### AWS Services Documentation
- [Amazon VPC](https://docs.aws.amazon.com/vpc/)
- [Amazon RDS](https://docs.aws.amazon.com/rds/)
- [Amazon ECS](https://docs.aws.amazon.com/ecs/)
- [AWS Lambda](https://docs.aws.amazon.com/lambda/)
- [Amazon CloudFront](https://docs.aws.amazon.com/cloudfront/)

### Terraform Resources
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)

### PostGIS Documentation
- [PostGIS Manual](https://postgis.net/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## 🆘 Support

For infrastructure-related issues:

1. **Check CloudWatch logs** for error messages
2. **Review Terraform state** for resource status
3. **Validate security groups** and network connectivity
4. **Monitor resource utilization** and limits
5. **Contact AWS Support** for service-specific issues

## 📄 License

This infrastructure code is part of the Property Assessment System project. Please refer to the main project license for usage terms.

---

**Note:** Always review and test infrastructure changes in a non-production environment before deploying to production. Ensure you understand the cost implications of the resources being created.