# Render Deployment Guide

This guide walks through deploying the Backyard Builder Finder API to Render with Supabase as the database backend.

## Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **Supabase Project**: Set up at [supabase.com](https://supabase.com)
3. **GitHub Repository**: Code pushed to GitHub
4. **Domain** (optional): For custom domain setup

## Step 1: Supabase Setup

### 1.1 Create Supabase Project

1. Go to [app.supabase.com](https://app.supabase.com)
2. Create new project with:
   - Strong database password
   - Region close to your users
   - Free tier is sufficient to start

### 1.2 Run Database Migrations

In Supabase SQL Editor, run the migrations in order:

```sql
-- Run each file from supabase/migrations/
-- 1. 20240814000001_initial_schema.sql
-- 2. 20240814000002_rls_policies.sql  
-- 3. 20240814000003_job_queue.sql
```

### 1.3 Get Connection Details

From Supabase Settings > Database:

- **Connection String**: `postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres`
- **Direct Connection**: For migrations only
- **Pooler Connection**: For application use

From Settings > API:

- **Project URL**: `https://[project-ref].supabase.co`
- **Anon Key**: Public key for client-side
- **Service Role Key**: Secret key for server-side

### 1.4 Configure Storage

1. Go to Storage in Supabase dashboard
2. Create bucket named `exports`
3. Set bucket to private (RLS enabled)

## Step 2: Render Setup

### 2.1 Connect GitHub

1. Log in to [render.com](https://render.com)
2. Go to Dashboard > New > Web Service
3. Connect your GitHub account
4. Select the repository

### 2.2 Configure Service

Use these settings:

- **Name**: `backyard-builder-api`
- **Region**: Oregon (or closest to Supabase)
- **Branch**: `main`
- **Runtime**: Python 3
- **Build Command**: 
  ```bash
  pip install --upgrade pip && pip install -r requirements.txt
  ```
- **Start Command**:
  ```bash
  uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1
  ```
- **Plan**: Free (upgrade as needed)

### 2.3 Environment Variables

In Render dashboard, set these environment variables:

#### Required Secrets (must set manually):

```bash
# Supabase Connection
DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres?pgbouncer=true
SYNC_DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres

# Supabase API
SUPABASE_URL=https://[project-ref].supabase.co
SUPABASE_ANON_KEY=eyJ... (your anon key)
SUPABASE_SERVICE_ROLE_KEY=eyJ... (your service role key)

# NextAuth (from Netlify deployment)
NEXTAUTH_URL=https://your-app.netlify.app
NEXTAUTH_SECRET=[generate with: openssl rand -base64 32]

# OAuth (if using)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

#### Auto-generated (Render will create):

```bash
# Click "Generate" for these in Render:
JWT_SECRET
ENCRYPTION_SECRET_KEY
```

#### Pre-configured (already in render.yaml):

All other environment variables are pre-configured in `render.yaml`.

### 2.4 Deploy

1. Click "Create Web Service"
2. Wait for build and deploy (5-10 minutes)
3. Check logs for any errors
4. Visit `https://[your-app].onrender.com/health`

## Step 3: Post-Deployment

### 3.1 Test Health Endpoint

```bash
curl https://your-api.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "providers": {
    "storage": {"configured": true, "healthy": true},
    "queue": {"configured": true, "healthy": true},
    "secrets": {"configured": true, "healthy": true},
    "metrics": {"configured": true, "healthy": true}
  },
  "version": "1.0.0",
  "environment": "production"
}
```

### 3.2 Configure CORS

Update CORS_ORIGINS in Render environment variables:

```bash
CORS_ORIGINS=https://your-frontend.netlify.app,https://your-custom-domain.com
```

### 3.3 Set Up Custom Domain (Optional)

1. In Render Dashboard > Settings > Custom Domains
2. Add your domain: `api.yourdomain.com`
3. Configure DNS with provided CNAME record
4. Enable auto-renew SSL

### 3.4 Configure Auto-Deploy

1. In Render Dashboard > Settings > Build & Deploy
2. Enable "Auto-Deploy" for main branch
3. Optional: Enable PR previews

## Step 4: Monitoring

### 4.1 Render Metrics

- View in Dashboard > Metrics
- Monitor: Memory, CPU, Response times
- Set up alerts for failures

### 4.2 Logs

- View in Dashboard > Logs
- Filter by: Web, Deploy, System
- Search and export capabilities

### 4.3 Supabase Monitoring

- Database: Settings > Database > Statistics
- API: Settings > API > Metrics
- Storage: Storage > Usage

## Step 5: Scaling

### When to Upgrade

Free tier limits:
- 512MB RAM
- 0.1 CPU
- Spins down after 15 min inactivity

Upgrade to Starter ($7/mo) when:
- Consistent traffic
- Need always-on service
- Memory usage > 400MB

### Scaling Options

1. **Vertical Scaling**: Upgrade Render plan
   - Starter: 512MB RAM, 0.5 CPU
   - Standard: 2GB RAM, 1 CPU
   - Pro: 4GB+ RAM, 2+ CPU

2. **Horizontal Scaling**: Multiple instances
   - Available on Standard+ plans
   - Auto-scaling based on CPU/memory

3. **Database Scaling**: Upgrade Supabase
   - Free: 500MB, 2 concurrent connections
   - Pro: 8GB, 60 concurrent connections
   - Team: 16GB+, 200+ connections

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check DATABASE_URL format
   - Ensure using pooler connection
   - Verify Supabase project is active

2. **Build Fails**
   - Check Python version (3.9+)
   - Verify requirements.txt
   - Check build logs

3. **Memory Errors**
   - Reduce worker count to 1
   - Upgrade to paid plan
   - Optimize code for memory

4. **Slow Cold Starts**
   - Normal on free tier (15-30s)
   - Upgrade for always-on
   - Implement health check pings

### Debug Commands

SSH into service (Starter+ plans):
```bash
render ssh [service-name]
```

View environment:
```bash
env | grep -E "(DATABASE|SUPABASE|STORAGE)"
```

Test database connection:
```bash
python -c "from core.database import check_database_health; import asyncio; print(asyncio.run(check_database_health()))"
```

## Security Best Practices

1. **Never commit secrets** to repository
2. **Use environment variables** for all sensitive data
3. **Enable 2FA** on Render and Supabase
4. **Rotate keys regularly** (every 90 days)
5. **Use RLS policies** in Supabase
6. **Implement rate limiting** in API
7. **Monitor for suspicious activity**
8. **Keep dependencies updated**

## Cost Optimization

### Free Tier Setup
- Render: Free web service
- Supabase: Free project
- Total: $0/month

### Production Setup ($14/month)
- Render Starter: $7/month
- Supabase Pro: $25/month (or stay on free)
- Redis Cache: Free tier
- Total: $7-32/month

### Enterprise Setup
- Render Standard+: $25+/month
- Supabase Team: $599/month
- Redis Paid: $15+/month
- CDN: CloudFlare free
- Total: $640+/month

## Migration to AWS

If you need to migrate to AWS later:

1. **Change environment variables**:
   ```bash
   STORAGE_PROVIDER=s3
   QUEUE_PROVIDER=sqs
   SECRETS_PROVIDER=kms
   METRICS_PROVIDER=cloudwatch
   ```

2. **Update connection strings** to RDS

3. **Deploy to ECS/EKS** instead of Render

4. **Data migration** using pg_dump/restore

The provider abstraction pattern makes this migration seamless!