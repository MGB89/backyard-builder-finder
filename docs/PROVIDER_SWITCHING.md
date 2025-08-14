# Provider Switching Guide

This guide explains how to switch between different infrastructure providers (low-cost vs AWS) using the provider abstraction pattern.

## Overview

The system supports two infrastructure stacks:
1. **Low-Cost Stack**: Supabase + Render + Netlify
2. **AWS Stack**: RDS + S3 + SQS + KMS + ECS/CloudFront

Switching between stacks requires only environment variable changes - no code modifications needed.

## Current Architecture

```mermaid
graph TB
    subgraph "Application Layer"
        API[FastAPI Backend]
        WEB[Next.js Frontend]
    end
    
    subgraph "Provider Abstraction Layer"
        SP[Storage Provider]
        QP[Queue Provider]
        SeP[Secrets Provider]
        MP[Metrics Provider]
    end
    
    subgraph "Low-Cost Stack"
        SUP[Supabase Storage]
        PGB[pg-boss Queue]
        APP[App Encryption]
        OTEL[OpenTelemetry]
    end
    
    subgraph "AWS Stack"
        S3[AWS S3]
        SQS[AWS SQS]
        KMS[AWS KMS]
        CW[CloudWatch]
    end
    
    API --> SP & QP & SeP & MP
    SP --> SUP & S3
    QP --> PGB & SQS
    SeP --> APP & KMS
    MP --> OTEL & CW
```

## Provider Configurations

### Storage Provider

**Supabase Storage** (Default):
```bash
STORAGE_PROVIDER=supabase
SUPABASE_URL=https://[ref].supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
STORAGE_BUCKET=exports
```

**AWS S3**:
```bash
STORAGE_PROVIDER=s3
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET=backyard-builder-exports
```

### Queue Provider

**pg-boss** (Default):
```bash
QUEUE_PROVIDER=pgboss
DATABASE_URL=postgresql://...
```

**AWS SQS**:
```bash
QUEUE_PROVIDER=sqs
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

### Secrets Provider

**App-level Encryption** (Default):
```bash
SECRETS_PROVIDER=app
ENCRYPTION_SECRET_KEY=your-32-char-key
ENCRYPTION_KEY_VERSION=1
```

**AWS KMS**:
```bash
SECRETS_PROVIDER=kms
AWS_REGION=us-west-2
KMS_KEY_ID=arn:aws:kms:us-west-2:...
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

### Metrics Provider

**OpenTelemetry** (Default):
```bash
METRICS_PROVIDER=otel
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://localhost:4318
SERVICE_NAME=backyard-builder-api
SERVICE_VERSION=1.0.0
```

**AWS CloudWatch**:
```bash
METRICS_PROVIDER=cloudwatch
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

## Switching Scenarios

### Scenario 1: Development to Production (Low-Cost)

Start with local development:
```bash
# .env.local
STORAGE_PROVIDER=supabase
QUEUE_PROVIDER=pgboss
SECRETS_PROVIDER=app
METRICS_PROVIDER=otel
SUPABASE_URL=http://localhost:54321
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
```

Deploy to production (Render):
```bash
# Set in Render Dashboard
STORAGE_PROVIDER=supabase
QUEUE_PROVIDER=pgboss
SECRETS_PROVIDER=app
METRICS_PROVIDER=otel
SUPABASE_URL=https://[prod-ref].supabase.co
DATABASE_URL=postgresql://[prod-connection-string]
```

### Scenario 2: Low-Cost to AWS Migration

Current (Supabase/Render):
```bash
STORAGE_PROVIDER=supabase
QUEUE_PROVIDER=pgboss
SECRETS_PROVIDER=app
METRICS_PROVIDER=otel
```

Migrate to AWS:
```bash
# Phase 1: Storage only
STORAGE_PROVIDER=s3
QUEUE_PROVIDER=pgboss  # Keep pg-boss
SECRETS_PROVIDER=app    # Keep app encryption
METRICS_PROVIDER=otel   # Keep OpenTelemetry

# Phase 2: Add Queue
STORAGE_PROVIDER=s3
QUEUE_PROVIDER=sqs
SECRETS_PROVIDER=app
METRICS_PROVIDER=otel

# Phase 3: Full AWS
STORAGE_PROVIDER=s3
QUEUE_PROVIDER=sqs
SECRETS_PROVIDER=kms
METRICS_PROVIDER=cloudwatch
```

### Scenario 3: Hybrid Configuration

Use AWS for critical services, low-cost for others:
```bash
STORAGE_PROVIDER=s3        # AWS for reliable storage
QUEUE_PROVIDER=pgboss      # PostgreSQL for simple queuing
SECRETS_PROVIDER=kms       # AWS for security compliance
METRICS_PROVIDER=otel      # OpenTelemetry for flexibility
```

## Migration Steps

### Step 1: Data Migration

#### Storage Migration (Supabase → S3)
```python
# Migration script example
import asyncio
from services.providers import get_storage_provider

async def migrate_storage():
    # Get both providers
    old_provider = SupabaseStorageProvider(...)
    new_provider = S3StorageProvider(...)
    
    # List all objects
    objects = await old_provider.list_objects()
    
    # Copy each object
    for obj in objects:
        data = await old_provider.get_object(obj.key)
        await new_provider.put_object(obj.key, data)
        print(f"Migrated: {obj.key}")

asyncio.run(migrate_storage())
```

#### Database Migration (Supabase → RDS)
```bash
# Export from Supabase
pg_dump $SUPABASE_URL > backup.sql

# Import to RDS
psql $RDS_URL < backup.sql
```

#### Queue Migration
```python
# Drain pg-boss queue before switching
async def drain_queue():
    pgboss = PgBossQueueProvider(...)
    
    # Process all remaining jobs
    while True:
        job = await pgboss.fetch_next()
        if not job:
            break
        # Process or re-queue to SQS
        await process_job(job)
```

### Step 2: Update Configuration

1. **Update environment variables** in deployment platform
2. **Restart services** to pick up new configuration
3. **Verify health endpoint** shows new providers

### Step 3: Validation

```bash
# Check provider health
curl https://api.example.com/health | jq .providers

# Expected response:
{
  "storage": {"configured": true, "healthy": true, "provider": "s3"},
  "queue": {"configured": true, "healthy": true, "provider": "sqs"},
  "secrets": {"configured": true, "healthy": true, "provider": "kms"},
  "metrics": {"configured": true, "healthy": true, "provider": "cloudwatch"}
}
```

### Step 4: Rollback Plan

If issues arise, revert environment variables:
```bash
# Quick rollback
STORAGE_PROVIDER=supabase
QUEUE_PROVIDER=pgboss
SECRETS_PROVIDER=app
METRICS_PROVIDER=otel
```

## Testing Provider Switching

### Local Testing

```bash
# Test with low-cost stack
export STORAGE_PROVIDER=supabase
export QUEUE_PROVIDER=pgboss
python -m pytest tests/

# Test with AWS stack
export STORAGE_PROVIDER=s3
export QUEUE_PROVIDER=sqs
python -m pytest tests/
```

### Integration Tests

```python
# tests/test_provider_switching.py
import os
import pytest
from services.providers import get_storage_provider

@pytest.mark.parametrize("provider", ["supabase", "s3"])
def test_storage_provider_switching(provider, monkeypatch):
    monkeypatch.setenv("STORAGE_PROVIDER", provider)
    
    storage = get_storage_provider()
    assert storage is not None
    
    # Test basic operations
    storage.put_object("test.txt", b"test data")
    data = storage.get_object("test.txt")
    assert data == b"test data"
```

### Performance Comparison

| Operation | Supabase | AWS S3 | Notes |
|-----------|----------|--------|-------|
| Upload 1MB | ~200ms | ~150ms | S3 slightly faster |
| Download 1MB | ~180ms | ~140ms | S3 edge locations help |
| List 1000 objects | ~300ms | ~250ms | Similar performance |
| Signed URL | ~50ms | ~30ms | Both fast enough |

| Operation | pg-boss | AWS SQS | Notes |
|-----------|---------|---------|-------|
| Enqueue | ~20ms | ~30ms | pg-boss faster locally |
| Dequeue | ~25ms | ~35ms | Network latency affects SQS |
| Throughput | 1000/s | 10000/s | SQS scales better |

## Cost Analysis

### Low-Cost Stack (Monthly)

| Service | Free Tier | Paid Tier | Notes |
|---------|-----------|-----------|-------|
| Supabase | $0 | $25 | 500MB storage, 2GB bandwidth |
| Render | $0 | $7 | Free spins down, Starter always-on |
| Netlify | $0 | $19 | 100GB bandwidth |
| **Total** | **$0** | **$51** | Production-ready |

### AWS Stack (Monthly)

| Service | Cost | Notes |
|---------|------|-------|
| RDS PostgreSQL | $15 | t3.micro, 20GB |
| S3 | $5 | 100GB storage, 1TB transfer |
| SQS | $2 | 1M requests |
| KMS | $1 | Key + operations |
| ECS Fargate | $30 | 0.5 vCPU, 1GB RAM |
| CloudFront | $10 | 1TB transfer |
| **Total** | **$63** | Scalable |

## Decision Matrix

| Factor | Low-Cost Stack | AWS Stack | Winner |
|--------|---------------|-----------|--------|
| Initial Cost | $0 | $63/month | Low-Cost |
| Scalability | Limited | Unlimited | AWS |
| Setup Complexity | Simple | Complex | Low-Cost |
| Vendor Lock-in | Minimal | High | Low-Cost |
| Enterprise Features | Basic | Full | AWS |
| Compliance | Basic | Full (HIPAA, SOC2) | AWS |
| Global Reach | Limited | Worldwide | AWS |
| Support | Community | Enterprise | AWS |

## Recommendations

### Start with Low-Cost Stack when:
- MVP or proof of concept
- < 1000 daily active users
- Budget < $100/month
- Single region deployment
- Standard compliance needs

### Migrate to AWS when:
- > 10,000 daily active users
- Need multi-region deployment
- Enterprise compliance required
- Budget > $500/month
- Need advanced features (ML, Analytics)

### Use Hybrid when:
- Specific AWS services needed (e.g., Rekognition)
- Want to minimize costs
- Testing AWS migration
- Need gradual transition

## Troubleshooting

### Provider Not Found
```python
# Error: Provider not initialized
# Solution: Check environment variables
import os
print(os.getenv("STORAGE_PROVIDER"))  # Should be "supabase" or "s3"
```

### Authentication Failures
```python
# Error: 403 Forbidden
# Solution: Check credentials
- Supabase: Verify service role key
- AWS: Check IAM permissions
```

### Connection Issues
```python
# Error: Connection timeout
# Solution: Check network and endpoints
- Verify URLs are correct
- Check firewall rules
- Test with curl/wget
```

### Performance Issues
```python
# Slow operations
# Solution: Check provider configuration
- Enable connection pooling
- Use appropriate instance sizes
- Check network latency
```

## Monitoring Provider Health

### Automated Health Checks
```python
# services/health_monitor.py
async def check_all_providers():
    results = {}
    
    # Check each provider
    for provider_type in ["storage", "queue", "secrets", "metrics"]:
        try:
            provider = get_provider(provider_type)
            health = await provider.health_check()
            results[provider_type] = health
        except Exception as e:
            results[provider_type] = {"healthy": False, "error": str(e)}
    
    return results
```

### Alerting
```yaml
# prometheus/alerts.yml
groups:
  - name: provider_health
    rules:
      - alert: ProviderDown
        expr: provider_health_status == 0
        for: 5m
        annotations:
          summary: "Provider {{ $labels.provider }} is down"
```

## Future Enhancements

1. **Auto-switching on failure** - Fallback to alternate provider
2. **Multi-provider support** - Use multiple providers simultaneously  
3. **Provider analytics** - Track usage and costs per provider
4. **Migration automation** - One-click provider migration
5. **Provider marketplace** - Support for additional providers (Azure, GCP)