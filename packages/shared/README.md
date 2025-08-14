# @property-assessment/shared

Shared TypeScript types, utilities, and API client for the Property Assessment application.

## Installation

```bash
npm install @property-assessment/shared
# or
yarn add @property-assessment/shared
# or
pnpm add @property-assessment/shared
```

## Usage

### Types

```typescript
import { Parcel, Assessment, User, Organization } from '@property-assessment/shared';

// Use the types in your application
const parcel: Parcel = {
  id: '123',
  parcelNumber: 'ABC-123-456',
  // ... other properties
};
```

### API Client

```typescript
import { ApiClient } from '@property-assessment/shared';

// Create an API client instance
const apiClient = new ApiClient({
  baseUrl: 'https://api.property-assessment.com',
  timeout: 30000,
  onUnauthorized: () => {
    // Handle unauthorized responses
    console.log('User is not authorized');
  },
});

// Set authentication token
apiClient.setAccessToken('your-jwt-token');

// Use the client
const parcels = await apiClient.searchParcels({
  criteria: {
    propertyType: ['residential'],
    valueRange: { min: 100000, max: 500000 }
  }
});
```

### Utilities

```typescript
import { 
  formatCurrency, 
  formatAddress, 
  validateParcel,
  calculateTotalValue 
} from '@property-assessment/shared';

// Formatting
const price = formatCurrency(250000); // "$250,000"
const address = formatAddress({
  street: "123 Main St",
  city: "Anytown",
  state: "ST",
  zipCode: "12345"
}); // "123 Main St, Anytown, ST 12345"

// Validation
const validation = validateParcel(parcel);
if (!validation.isValid) {
  console.log('Validation errors:', validation.errors);
}

// Calculations
const total = calculateTotalValue(200000, 150000); // 350000
```

## Available Types

### Core Types
- `User` - User account information
- `Organization` - Assessment organization details
- `Parcel` - Property parcel data
- `Assessment` - Property assessment records
- `Improvement` - Building and structure details

### Request/Response Types
- `ApiResponse<T>` - Standard API response wrapper
- `PaginatedResponse<T>` - Paginated response format
- `LoginRequest/Response` - Authentication types
- `ParcelSearchRequest/Response` - Search functionality
- Various CRUD operation types

### GeoJSON Types
- `GeoJSONFeature` - Standard GeoJSON feature
- `ParcelFeature` - Property-specific GeoJSON feature
- `ParcelFeatureCollection` - Collection of parcel features

### Filter Types
- `Filter` - Flexible filtering system
- `ParcelFilters` - Property-specific filters
- `AssessmentFilters` - Assessment-specific filters

### Export Types
- `ExportConfig` - Export configuration options
- `ExportJob` - Export job tracking
- Various format-specific options (CSV, Excel, PDF, etc.)

## API Client Features

- **Type-safe requests** - All endpoints are fully typed
- **Automatic retries** - Configurable retry logic for failed requests
- **Error handling** - Structured error responses
- **Authentication** - JWT token management
- **Request timeouts** - Configurable timeout settings
- **Interceptors** - Custom request/response handling

## Utility Functions

### Validation
- `validateUser()` - Validate user data
- `validateOrganization()` - Validate organization data
- `validateParcel()` - Validate parcel data
- `validateAssessment()` - Validate assessment data

### Formatting
- `formatCurrency()` - Currency formatting
- `formatDate()` - Date formatting
- `formatAddress()` - Address formatting
- `formatPhoneNumber()` - Phone number formatting
- `formatCoordinates()` - Coordinate formatting

### Calculations
- `calculateTotalValue()` - Property value calculations
- `calculateTaxAmount()` - Tax calculations
- `calculateDepreciation()` - Depreciation calculations
- Various assessment approach calculations

## Development

### Building

```bash
npm run build
```

### Testing

```bash
npm run test
npm run test:watch
```

### Linting

```bash
npm run lint
npm run lint:fix
```

### Type Checking

```bash
npm run type-check
```

## License

ISC