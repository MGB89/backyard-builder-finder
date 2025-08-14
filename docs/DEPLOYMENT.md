# Deployment Guide

## Local Development Setup

### 1. Database Setup
```bash
# Start PostgreSQL with PostGIS
docker run -d \
  --name bbf-postgres \
  -e POSTGRES_DB=backyard_builder \
  -e POSTGRES_USER=bbf_user \
  -e POSTGRES_PASSWORD=dev_password \
  -p 5432:5432 \
  postgis/postgis:15-3.4

# Run migrations
cd apps/api
alembic upgrade head
```

### 2. Start Services
```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or manually:
# Start Redis
docker run -d --name bbf-redis -p 6379:6379 redis:7-alpine

# Start API
cd apps/api
pip install -r requirements.txt
uvicorn main:app --reload

# Start Web
cd apps/web
pnpm install
pnpm dev
```

### 3. Configure Environment
```bash
# Copy environment templates
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.local.example apps/web/.env.local

# Update with your values (OAuth, API keys, etc.)
```

## Production Deployment (AWS)

### 1. Infrastructure Setup
```bash
cd infra
terraform init
terraform plan -var="environment=production"
terraform apply -var="environment=production"
```

### 2. Deploy via GitHub Actions
```bash
git push origin main
# GitHub Actions will handle the deployment
```

### 3. Manual Deployment
```bash
# Build and push Docker images
docker build -t bbf-api apps/api
docker tag bbf-api:latest <ecr-repo>/bbf-api:latest
docker push <ecr-repo>/bbf-api:latest

# Update ECS service
aws ecs update-service \
  --cluster bbf-production-cluster \
  --service bbf-production-api-service \
  --force-new-deployment
```

## Environment Variables

### Required for Production
- `DATABASE_URL` - PostgreSQL connection string with PostGIS
- `JWT_SECRET` - Strong secret for JWT signing
- `NEXTAUTH_SECRET` - Strong secret for NextAuth (32+ chars)
- `GOOGLE_CLIENT_ID/SECRET` - For Google OAuth
- `AZURE_AD_CLIENT_ID/SECRET/TENANT_ID` - For Microsoft OAuth

### Optional (Enhanced Features)
- `OPENAI_API_KEY` - For LLM-based zoning parsing
- `MAPBOX_TOKEN` - For enhanced geocoding
- `AWS_ACCESS_KEY_ID/SECRET` - For S3 exports

## Health Checks

- API Health: `https://api.yourdomain.com/health`
- Database: Automatic health checks via ALB
- Frontend: CloudFront health checks

## Monitoring

- CloudWatch Logs for application logs
- CloudWatch Metrics for performance
- X-Ray for distributed tracing (optional)

## Backup & Recovery

- RDS automated backups (7-day retention)
- Point-in-time recovery available
- S3 versioning for exports
- Database snapshots before major updates

## Scaling

- ECS auto-scaling based on CPU/memory
- RDS read replicas for read-heavy workloads
- CloudFront for global CDN
- ElastiCache for session storage (optional)

## Security Checklist

- [ ] SSL certificates configured
- [ ] Secrets in AWS Secrets Manager
- [ ] RLS policies enabled
- [ ] API rate limiting active
- [ ] WAF rules configured
- [ ] VPC security groups reviewed
- [ ] Audit logging enabled
- [ ] Backup strategy tested