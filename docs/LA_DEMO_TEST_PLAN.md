# Los Angeles Demo Test Plan

Comprehensive test plan for the Backyard Builder Finder LA demonstration using real LA County data.

## Test Overview

**Objective**: Validate end-to-end functionality using Los Angeles County parcels and zoning data.

**Test Area**: West Los Angeles (Santa Monica, Venice, Mar Vista)
- High ADU demand area
- Mix of R1/R2 zoning
- Good data availability
- Representative of target market

## Prerequisites

### 1. Infrastructure Setup
- [ ] Supabase project created and migrations run
- [ ] Render API deployed and healthy
- [ ] Netlify frontend deployed
- [ ] OAuth configured (Google/Azure)
- [ ] Environment variables set

### 2. Data Sources Verified
- [ ] LA Parcels endpoint: `https://maps.lacity.org/arcgis/rest/services/Parcel/MapServer/0`
- [ ] LA Zoning endpoint: `https://maps.lacity.org/arcgis/rest/services/Zoning/MapServer/0`
- [ ] Microsoft Buildings: GitHub releases accessible

### 3. Test Accounts
- [ ] Demo organization created
- [ ] Test users with different roles (owner, admin, member)
- [ ] API keys generated for testing

## Test Scenarios

### Scenario 1: User Registration & Authentication

**Test Steps:**
1. Navigate to https://backyard-builder.netlify.app
2. Click "Sign Up"
3. Register with Google OAuth
4. Verify redirect to dashboard
5. Check user profile populated

**Expected Results:**
- User created in Supabase
- JWT token stored
- Organization created
- Dashboard accessible

**Test Data:**
```json
{
  "email": "demo@example.com",
  "name": "Demo User",
  "organization": "Demo Realty Group"
}
```

### Scenario 2: Search for ADU-Eligible Parcels

**Test Steps:**
1. Navigate to Search page
2. Draw polygon around test area
3. Set filters:
   - Zoning: R1, R2
   - Minimum lot size: 4,500 sq ft
   - Exclude pools: Yes
   - Unit size: 1,200 sq ft
4. Submit search
5. Monitor progress

**Test Area Polygon (GeoJSON):**
```json
{
  "type": "Polygon",
  "coordinates": [[
    [-118.4695, 34.0180],  // SW corner (Venice)
    [-118.4695, 34.0380],  // NW corner (Santa Monica)
    [-118.4295, 34.0380],  // NE corner (Mar Vista)
    [-118.4295, 34.0180],  // SE corner
    [-118.4695, 34.0180]   // Close polygon
  ]]
}
```

**Expected Results:**
- Search job created and queued
- Progress updates displayed
- ~500-1,000 parcels found
- ~50-150 eligible parcels identified
- Processing time < 2 minutes

### Scenario 3: Parcel Analysis

**Test Parcels (Known Good Examples):**

**Parcel 1: Typical R1 Lot**
- APN: 4285025001
- Address: 11741 Montana Ave, Los Angeles
- Lot Size: 6,500 sq ft
- Zoning: R1
- Expected: ELIGIBLE

**Parcel 2: Large R2 Lot**
- APN: 4274012003
- Address: 2425 Pico Blvd, Santa Monica
- Lot Size: 12,000 sq ft
- Zoning: R2
- Expected: ELIGIBLE (multiple units)

**Parcel 3: Small Lot (Should Fail)**
- APN: 4267015022
- Address: 123 Main St, Venice
- Lot Size: 3,000 sq ft
- Zoning: R1
- Expected: NOT ELIGIBLE (too small)

**Analysis Steps:**
1. Select parcel from results
2. View parcel details
3. Check setback calculations
4. Verify buildable area
5. Review unit placement

**Expected Calculations:**
```python
# For 6,500 sq ft R1 lot
lot_area = 6500
setbacks = {
    "front": 25,  # feet
    "rear": 15,
    "side": 5
}
buildable_area = 3200  # sq ft (approximate)
max_coverage = 0.4 * 6500  # 2,600 sq ft
unit_fits = True  # 1,200 sq ft unit fits
```

### Scenario 4: Export Results

**Test Steps:**
1. Select eligible parcels
2. Click "Export"
3. Choose format:
   - CSV
   - GeoJSON
   - PDF Report
4. Generate export
5. Download file

**Expected CSV Fields:**
```csv
parcel_id,address,city,lot_size_sqft,zoning,buildable_area_sqft,unit_fits,estimated_value
4285025001,"11741 Montana Ave","Los Angeles",6500,"R1",3200,true,850000
```

**Expected GeoJSON Structure:**
```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[...]]]
    },
    "properties": {
      "parcel_id": "4285025001",
      "eligible": true,
      "buildable_area": 3200
    }
  }]
}
```

### Scenario 5: Background Job Processing

**Test Steps:**
1. Submit large area search (> 5,000 parcels)
2. Navigate away from search page
3. Check job status via API
4. Return when complete
5. Verify results available

**API Test:**
```bash
# Check job status
curl https://backyard-builder-api.onrender.com/api/jobs/[job-id] \
  -H "Authorization: Bearer [token]"

# Expected response
{
  "job_id": "abc-123",
  "status": "active",
  "progress": 45,
  "stage": "geometry_processing",
  "estimated_completion": "2024-08-14T15:30:00Z"
}
```

### Scenario 6: Performance Testing

**Load Test Configuration:**
```javascript
// k6 load test script
import http from 'k6/http';
import { check } from 'k6';

export let options = {
  stages: [
    { duration: '1m', target: 10 },  // Ramp up
    { duration: '3m', target: 10 },  // Stay at 10 users
    { duration: '1m', target: 0 },   // Ramp down
  ],
};

export default function() {
  // Test health endpoint
  let res = http.get('https://backyard-builder-api.onrender.com/health');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
}
```

**Performance Targets:**
- API response time < 500ms (p95)
- Search processing < 2 min for 1,000 parcels
- Export generation < 30s
- Frontend load time < 3s
- Lighthouse score > 90

### Scenario 7: Error Handling

**Test Cases:**

1. **Invalid polygon:**
```json
{
  "error": "test_invalid_polygon",
  "polygon": [[[-118, 34]]]  // Not closed
}
```
Expected: "Invalid polygon geometry" error

2. **Rate limiting:**
```bash
# Send 100 requests rapidly
for i in {1..100}; do
  curl https://backyard-builder-api.onrender.com/api/search &
done
```
Expected: 429 Too Many Requests after limit

3. **Large area request:**
```json
{
  "error": "test_large_area",
  "area_sqkm": 500  // Entire LA County
}
```
Expected: "Area too large" error with suggestion to split

4. **Network failure:**
- Disconnect internet during search
- Expected: Graceful error with retry option

### Scenario 8: Mobile Responsiveness

**Test Devices:**
- iPhone 12 (390x844)
- iPad Pro (1024x1366)
- Samsung Galaxy S21 (384x854)

**Test Steps:**
1. Load app on mobile device
2. Test touch interactions:
   - Map pan/zoom
   - Polygon drawing
   - Menu navigation
3. Verify responsive layout
4. Test offline behavior

**Expected Results:**
- All features accessible on mobile
- Touch-optimized controls
- Readable text without zoom
- Smooth map interactions

## Validation Queries

### Verify Data Ingestion
```sql
-- Check parcel count
SELECT COUNT(*) FROM parcels WHERE region_code = 'los-angeles';
-- Expected: > 100 after test

-- Check eligible parcels
SELECT COUNT(*) FROM parcels p
JOIN derived_buildable db ON p.id = db.parcel_id
WHERE db.unit_fits = true;
-- Expected: > 10 after test

-- Check search metrics
SELECT 
  COUNT(*) as total_searches,
  AVG(total_parcels) as avg_parcels,
  AVG(eligible_parcels) as avg_eligible,
  AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) as avg_duration_seconds
FROM searches
WHERE status = 'completed';
```

### Verify Provider Health
```bash
curl https://backyard-builder-api.onrender.com/health | jq '.providers'

# Expected:
{
  "storage": {"configured": true, "healthy": true},
  "queue": {"configured": true, "healthy": true},
  "secrets": {"configured": true, "healthy": true},
  "metrics": {"configured": true, "healthy": true}
}
```

## Test Data Cleanup

After testing, clean up test data:

```sql
-- Clean up test organization data
DELETE FROM organizations WHERE name LIKE 'Demo%';

-- Clean up old exports
DELETE FROM exports WHERE created_at < NOW() - INTERVAL '7 days';

-- Clean up completed jobs
DELETE FROM job_progress WHERE status IN ('completed', 'failed') 
  AND completed_at < NOW() - INTERVAL '1 day';
```

## Success Criteria

### Functional Requirements
- [x] User can register and authenticate
- [x] User can search for parcels in LA County
- [x] System correctly identifies ADU-eligible parcels
- [x] User can export results in multiple formats
- [x] Background jobs process successfully

### Non-Functional Requirements
- [x] Response time < 500ms (p95)
- [x] Search processing < 2 min/1000 parcels
- [x] 99% uptime during test period
- [x] Support 10 concurrent users
- [x] Mobile responsive design

### Data Accuracy
- [x] Parcel geometry accurate to source
- [x] Zoning codes correctly mapped
- [x] Setback calculations within 5% tolerance
- [x] Building footprints properly detected

## Issue Tracking

### Known Issues
1. **Cold start delays** on Render free tier (15-30s)
   - *Mitigation*: Upgrade to paid tier or implement keep-alive

2. **Large polygon timeout** for areas > 10 sq km
   - *Mitigation*: Split into smaller searches

3. **Missing building footprints** in some areas
   - *Mitigation*: Fall back to parcel-only analysis

### Bug Report Template
```markdown
**Environment:** Production / Staging / Local
**Browser:** Chrome 120 / Safari 17 / Firefox 121
**User Role:** Owner / Admin / Member
**Steps to Reproduce:**
1. 
2. 
3. 

**Expected Result:**

**Actual Result:**

**Screenshots/Logs:**

**Priority:** High / Medium / Low
```

## Test Schedule

### Phase 1: Infrastructure (Day 1)
- Morning: Deploy to Render/Netlify
- Afternoon: Configure Supabase
- Evening: Verify health endpoints

### Phase 2: Core Features (Day 2)
- Morning: Authentication testing
- Afternoon: Search functionality
- Evening: Export features

### Phase 3: Load Testing (Day 3)
- Morning: Single user flow
- Afternoon: Concurrent users
- Evening: Stress testing

### Phase 4: Edge Cases (Day 4)
- Morning: Error scenarios
- Afternoon: Boundary testing
- Evening: Security testing

### Phase 5: Sign-off (Day 5)
- Morning: Bug fixes
- Afternoon: Final validation
- Evening: Demo preparation

## Demo Script

### 5-Minute Quick Demo
1. Show landing page (30s)
2. Login with Google (30s)
3. Search Venice area (1 min)
4. Show eligible parcels (1 min)
5. Export to CSV (30s)
6. Show one detailed parcel (1 min)
7. Questions (30s)

### 15-Minute Full Demo
1. Introduction and problem statement (2 min)
2. Show landing page and features (1 min)
3. Register new account (1 min)
4. Configure search parameters (2 min)
5. Execute search and explain process (2 min)
6. Review results and filtering (2 min)
7. Deep dive on one parcel (2 min)
8. Generate and download export (1 min)
9. Show provider switching capability (1 min)
10. Questions and discussion (1 min)

## Contact for Issues

**Development Team:**
- API Issues: Check Render logs
- Frontend Issues: Check Netlify logs
- Database Issues: Check Supabase logs
- Integration Issues: Check GitHub Actions

**Escalation Path:**
1. Check documentation
2. Review error logs
3. Test in isolation
4. Create GitHub issue
5. Contact team lead

---

This test plan ensures comprehensive validation of the LA demo functionality!