# Backyard Builder Finder - Production Ready

✅ **FULLY IMPLEMENTED** - A production-ready, multi-tenant SaaS platform for finding buildable backyard spaces in residential parcels with PostGIS spatial analysis, SSO authentication, and comprehensive search pipeline.

## 🏗️ Architecture Overview

This monorepo contains a full-stack property assessment platform with spatial analysis capabilities:

- **Frontend**: Next.js 14 with MapLibre GL for interactive mapping
- **Backend**: FastAPI with PostGIS for geoprocessing
- **Infrastructure**: AWS with Terraform IaC
- **Shared**: TypeScript package for shared types and utilities

## 📁 Project Structure

```
├── apps/
│   ├── api/          # FastAPI backend with geoprocessing
│   └── web/          # Next.js frontend with MapLibre
├── packages/
│   └── shared/       # Shared TypeScript types and utilities
├── infra/            # Terraform AWS infrastructure
├── ops/              # CI/CD pipelines and DevOps
├── docs/             # Documentation
├── scripts/          # Utility scripts
└── examples/         # Example configurations
```

## ✅ Implementation Status

**ALL FEATURES IMPLEMENTED:**
- ✅ Full multi-tenant backend (FastAPI + PostGIS) with RLS and migrations
- ✅ Complete search pipeline & APIs (area search → staged filters → geometry → optional CV → zoning rules → fit test)
- ✅ Proper SSO (Google/Microsoft) via NextAuth with working /api/auth endpoints
- ✅ Frontend: robust filters, map overlays, parcel drawers, cost guardrails, exports (CSV/GeoJSON/PDF)
- ✅ LA City pilot: ready-to-run saved search (1,200 sq ft, pool=exclude)
- ✅ Cost & speed controls: caching, batching, rate limits, per-org budgets, LLM minimal/strategic
- ✅ Docs, tests, CI/CD; no licensed imagery stored

## 🚀 Quick Start

### Prerequisites

- Node.js 20+
- Python 3.11+
- pnpm 8+
- Docker and Docker Compose
- PostgreSQL with PostGIS extension
- AWS Account (for deployment)

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/backyard-builder-finder.git
cd backyard-builder-finder
```

2. **Install dependencies**
```bash
# Install pnpm globally
npm install -g pnpm

# Install all dependencies
pnpm install
```

3. **Set up environment variables**
```bash
# Web app
cp apps/web/.env.local.example apps/web/.env.local

# API
cp apps/api/.env.example apps/api/.env
```

4. **Start the development environment**
```bash
# Start all services with Docker Compose
docker-compose up -d

# Or run services individually:
# Start the API
cd apps/api
pip install -r requirements.txt
uvicorn main:app --reload

# Start the web app
cd apps/web
pnpm dev
```

5. **Access the applications**
- Web App: http://localhost:3000
- API Documentation: http://localhost:8000/docs
- PostgreSQL: localhost:5432

## 🏃 Running Tests

```bash
# Run all tests
pnpm test

# Run web tests
pnpm --filter web test

# Run API tests
cd apps/api && pytest

# Run E2E tests
pnpm --filter web test:e2e
```

## 📊 Database Setup

The application uses PostgreSQL with PostGIS for spatial data:

```bash
# Run migrations
cd apps/api
alembic upgrade head

# Seed sample data (development only)
python scripts/seed_data.py
```

## 🗺️ LA City Pilot

To run the LA City demonstration:

1. Configure LA data sources in `apps/api/.env`:
```env
LA_PARCELS_ENDPOINT=https://maps.lacity.org/arcgis/rest/services/...
LA_ZONING_ENDPOINT=https://maps.lacity.org/arcgis/rest/services/...
```

2. Ingest LA parcel data:
```bash
curl -X POST http://localhost:8000/admin/ingest/parcels?region=los-angeles \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

3. Run the demo search:
```bash
curl -X POST http://localhost:8000/search/execute \
  -H "Content-Type: application/json" \
  -d '{
    "area": {"type": "city", "name": "Los Angeles"},
    "filters": {
      "unitSize": 1200,
      "excludePools": true
    }
  }'
```

## 🔑 API Keys Configuration

The platform supports multiple third-party services. Configure these in your environment:

### Required Keys
- **JWT_SECRET**: For authentication
- **DATABASE_URL**: PostgreSQL connection string

### Optional Keys (for enhanced features)
- **OPENAI_API_KEY**: For LLM-powered zoning rule parsing
- **ANTHROPIC_API_KEY**: Alternative LLM provider
- **MAPBOX_TOKEN**: For enhanced geocoding and tiles
- **GOOGLE_MAPS_API_KEY**: For Google geocoding
- **RESO_CLIENT_ID/SECRET**: For MLS listings

## 🚢 Deployment

### AWS Deployment with Terraform

1. **Configure AWS credentials**
```bash
aws configure
```

2. **Initialize Terraform**
```bash
cd infra
terraform init
```

3. **Create terraform.tfvars**
```bash
cp terraform.tfvars.example terraform.tfvars
# Edit with your configuration
```

4. **Deploy infrastructure**
```bash
terraform plan
terraform apply
```

5. **Deploy applications**
```bash
# Deploy via GitHub Actions
git push origin main

# Or manually deploy
./scripts/deploy.sh production
```

## 📝 API Examples

### Search for Parcels
```bash
curl -X POST http://localhost:8000/search/preview \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "area": {
      "type": "city",
      "name": "Los Angeles"
    },
    "filters": {
      "unitSize": 1200,
      "excludePools": true,
      "zoningCodes": ["R1", "R2"],
      "maxLotCoverage": 0.4
    }
  }'
```

### Export Results
```bash
curl -X POST http://localhost:8000/exports \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "searchId": "search_123",
    "format": "geojson",
    "includeAnalysis": true
  }'
```

### Get Parcel Details
```bash
curl http://localhost:8000/parcels/12345 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🔒 Security Considerations

- All user API keys are encrypted using AWS KMS
- Row-level security (RLS) enforced in PostgreSQL
- JWT authentication for API access
- Rate limiting and budget controls per organization
- Audit logging for compliance
- No storage of licensed imagery data
- Portal scraping disabled by default (requires explicit ToS acceptance)

## 📚 Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [API Documentation](http://localhost:8000/docs)
- [Zoning Rules Schema](docs/ZONING_RULES_SCHEMA.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Contributing Guidelines](docs/CONTRIBUTING.md)

## 🤝 Contributing

Please read our [Contributing Guidelines](docs/CONTRIBUTING.md) before submitting PRs.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Legal Notice

This software is provided for legitimate property assessment purposes only. Users are responsible for:
- Complying with all local, state, and federal regulations
- Respecting property data usage terms and conditions
- Obtaining necessary permissions for data access
- Ensuring compliance with MLS and real estate data regulations

Portal scraping features are DISABLED by default and require explicit ToS acceptance.

## 🆘 Support

- GitHub Issues: [Report bugs or request features](https://github.com/yourusername/backyard-builder-finder/issues)
- Documentation: [Full documentation](docs/)
- Email: support@backyardbuilderfinder.com

## 🎯 Roadmap

- [ ] Mobile application (React Native)
- [ ] Advanced ML models for property valuation
- [ ] Integration with more MLS systems
- [ ] 3D visualization of buildable spaces
- [ ] Automated permit checking
- [ ] Construction cost estimation

---

Built with ❤️ for property assessment professionals