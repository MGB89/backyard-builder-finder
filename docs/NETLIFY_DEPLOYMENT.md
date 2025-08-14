# Netlify Deployment Guide

This guide walks through deploying the Backyard Builder Finder frontend to Netlify.

## Prerequisites

1. **Netlify Account**: Sign up at [netlify.com](https://netlify.com)
2. **GitHub Repository**: Code pushed to GitHub
3. **Render API**: Backend deployed (see RENDER_DEPLOYMENT.md)
4. **OAuth Apps** (optional): Google/Azure AD configured

## Step 1: OAuth Setup (Optional)

### 1.1 Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized redirect URIs:
     - `https://your-app.netlify.app/api/auth/callback/google`
     - `http://localhost:3000/api/auth/callback/google` (dev)
5. Save Client ID and Client Secret

### 1.2 Microsoft Azure AD

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to Azure Active Directory > App registrations
3. New registration:
   - Supported account types: Multitenant
   - Redirect URI: `https://your-app.netlify.app/api/auth/callback/azure-ad`
4. Create client secret
5. Note Application ID, Client Secret, and Tenant ID

## Step 2: Netlify Setup

### 2.1 Import from GitHub

1. Log in to [app.netlify.com](https://app.netlify.com)
2. Click "Add new site" > "Import an existing project"
3. Choose GitHub
4. Select your repository
5. Configure build settings:

```yaml
Base directory: apps/web
Build command: npm run build
Publish directory: apps/web/.next
```

### 2.2 Environment Variables

In Netlify Dashboard > Site Settings > Environment Variables, add:

#### Required Variables:

```bash
# NextAuth Configuration
NEXTAUTH_URL=https://your-app-name.netlify.app
NEXTAUTH_SECRET=[generate with: openssl rand -base64 32]

# Database (Supabase connection string)
DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres

# API Backend (your Render URL)
NEXT_PUBLIC_API_URL=https://backyard-builder-api.onrender.com

# Supabase (for direct client access)
NEXT_PUBLIC_SUPABASE_URL=https://[ref].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

#### OAuth Variables (if using):

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Azure AD OAuth
AZURE_AD_CLIENT_ID=your-app-id
AZURE_AD_CLIENT_SECRET=your-client-secret
AZURE_AD_TENANT_ID=your-tenant-id
```

#### Optional Map Providers:

```bash
# Choose one or more
NEXT_PUBLIC_MAPBOX_TOKEN=pk.eyJ...
NEXT_PUBLIC_GOOGLE_MAPS_KEY=AIza...
NEXT_PUBLIC_MAPTILER_KEY=...
```

### 2.3 Deploy

1. Click "Deploy site"
2. Wait for build (3-5 minutes)
3. Check deploy log for errors
4. Visit your site at `https://[name].netlify.app`

## Step 3: Post-Deployment Configuration

### 3.1 Update Callback URLs

After deployment, update OAuth providers with actual Netlify URL:

**Google Cloud Console:**
- Add: `https://your-actual-site.netlify.app/api/auth/callback/google`

**Azure Portal:**
- Add: `https://your-actual-site.netlify.app/api/auth/callback/azure-ad`

### 3.2 Configure Custom Domain (Optional)

1. Netlify Dashboard > Domain Settings
2. Add custom domain: `app.yourdomain.com`
3. Configure DNS:
   - Option 1: Point nameservers to Netlify
   - Option 2: Add CNAME record
4. Enable automatic HTTPS

### 3.3 Update Environment Variables

Update these with production values:

```bash
# Update with custom domain
NEXTAUTH_URL=https://app.yourdomain.com

# Update API CORS
# (In Render dashboard, add your domain to CORS_ORIGINS)
```

### 3.4 Enable Netlify Features

1. **Forms**: For contact forms
2. **Identity**: For additional auth
3. **Functions**: For serverless endpoints
4. **Analytics**: For traffic insights
5. **Split Testing**: For A/B tests

## Step 4: Continuous Deployment

### 4.1 Auto Deploy

Enabled by default:
- Pushes to `main` trigger production deploys
- PR creates preview deploys

### 4.2 Deploy Contexts

Configure in `netlify.toml`:

```toml
[context.production]
  environment = { NEXT_PUBLIC_ENV = "production" }

[context.staging]
  environment = { NEXT_PUBLIC_ENV = "staging" }

[context.deploy-preview]
  environment = { NEXT_PUBLIC_ENV = "preview" }
```

### 4.3 Deploy Notifications

1. Site Settings > Deploys > Deploy notifications
2. Add notifications for:
   - Deploy succeeded
   - Deploy failed
   - Deploy preview ready

## Step 5: Performance Optimization

### 5.1 Next.js Optimizations

Already configured in `netlify.toml`:
- Next.js plugin for optimal builds
- Image optimization
- Static asset caching
- ISR support

### 5.2 Lighthouse Monitoring

Automatic with plugin:
- Performance > 90%
- Accessibility > 90%
- Best Practices > 90%
- SEO > 90%

### 5.3 Bundle Analysis

```bash
# Local analysis
npm run analyze

# Check bundle size
npm run build
```

### 5.4 CDN Configuration

Netlify Edge:
- Global CDN included
- Automatic compression
- HTTP/2 & HTTP/3
- Brotli compression

## Step 6: Monitoring

### 6.1 Netlify Analytics

1. Enable in Dashboard > Analytics
2. Monitor:
   - Page views
   - Unique visitors
   - Top pages
   - Top sources
   - Bandwidth usage

### 6.2 Real User Monitoring

```javascript
// Add to _app.tsx for custom metrics
import { reportWebVitals } from 'next/web-vitals'

export function reportWebVitals(metric) {
  // Send to analytics service
  console.log(metric)
}
```

### 6.3 Error Tracking

Integrate Sentry (optional):

```bash
npm install @sentry/nextjs
```

```javascript
// sentry.client.config.js
Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_ENV,
})
```

## Step 7: Security

### 7.1 Security Headers

Already configured in `netlify.toml`:
- CSP (Content Security Policy)
- X-Frame-Options
- X-Content-Type-Options
- Referrer-Policy
- Permissions-Policy

### 7.2 Environment Variable Security

- Never expose secrets in NEXT_PUBLIC_* variables
- Use server-side only for sensitive data
- Rotate secrets regularly

### 7.3 DDoS Protection

Netlify includes:
- Rate limiting
- DDoS mitigation
- Bot protection (upgrade for advanced)

## Troubleshooting

### Common Issues

1. **Build Fails**
   ```bash
   # Check Node version
   NODE_VERSION=18
   
   # Clear cache and retry
   netlify deploy --clear-cache
   ```

2. **404 on Routes**
   - Check `redirects` in netlify.toml
   - Ensure SPA fallback configured

3. **API Connection Failed**
   - Verify NEXT_PUBLIC_API_URL
   - Check CORS settings on backend
   - Test API health endpoint

4. **OAuth Not Working**
   - Verify callback URLs match exactly
   - Check client ID/secret
   - Ensure NEXTAUTH_URL is correct

### Debug Commands

```bash
# Test build locally
cd apps/web
npm run build
npm run start

# Test with Netlify CLI
netlify dev

# Check environment
netlify env:list

# Manual deploy
netlify deploy --prod
```

### Logs

1. **Deploy logs**: Dashboard > Deploys > View logs
2. **Function logs**: Dashboard > Functions > View logs
3. **Browser console**: Check for client-side errors

## Cost Optimization

### Free Tier (Starter)
- 100GB bandwidth/month
- 300 build minutes/month
- Automatic deploys
- Preview deploys
- Total: $0/month

### Pro Tier ($19/month per member)
- 1TB bandwidth
- 1000 build minutes
- Background functions
- Analytics
- Password protection

### Business Tier
- 5TB bandwidth
- 2000 build minutes
- SSO/SAML
- Audit logs
- SLA

## Migration Guide

### To Vercel

1. Create `vercel.json`:
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs"
}
```

2. Import to Vercel
3. Set environment variables
4. Update DNS

### To AWS Amplify

1. Connect GitHub to Amplify
2. Configure build settings
3. Set environment variables
4. Update DNS

### To Self-Hosted

1. Build Docker image
2. Deploy to:
   - AWS ECS/EKS
   - Google Cloud Run
   - Azure Container Instances
3. Set up CDN (CloudFlare)
4. Configure SSL

## Best Practices

1. **Use Preview Deploys** for testing
2. **Enable build plugins** for optimization
3. **Monitor Core Web Vitals**
4. **Implement proper caching**
5. **Use environment variables** for config
6. **Keep dependencies updated**
7. **Regular security audits**
8. **Performance budgets**

## Support Resources

- [Netlify Docs](https://docs.netlify.com)
- [Next.js on Netlify](https://docs.netlify.com/frameworks/next-js)
- [Netlify Community](https://community.netlify.com)
- [Status Page](https://netlifystatus.com)