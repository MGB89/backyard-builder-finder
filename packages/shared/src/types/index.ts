/**
 * Main types export file for Property Assessment shared package
 */

// API types
export type {
  User,
  Organization,
  Parcel,
  Improvement,
  TaxExemption,
  Assessment,
  ComparableSale,
  SaleAdjustment,
  CostData,
  IncomeData,
  AssessmentDocument,
  SearchCriteria,
} from './api.js';

// Request/Response types
export type {
  PaginationParams,
  SortParams,
  ApiResponse,
  PaginatedResponse,
  LoginRequest,
  LoginResponse,
  RefreshTokenRequest,
  RefreshTokenResponse,
  CreateUserRequest,
  UpdateUserRequest,
  UsersListRequest,
  UsersListResponse,
  CreateOrganizationRequest,
  UpdateOrganizationRequest,
  OrganizationsListResponse,
  ParcelSearchRequest,
  ParcelSearchResponse,
  CreateParcelRequest,
  UpdateParcelRequest,
  CreateAssessmentRequest,
  UpdateAssessmentRequest,
  AssessmentsListRequest,
  AssessmentsListResponse,
  BulkUpdateRequest,
  BulkUpdateResponse,
  FileUploadRequest,
  FileUploadResponse,
  ExportRequest,
  ExportResponse,
  ExportStatusResponse,
} from './requests.js';

// GeoJSON types
export type {
  GeoJSONPosition,
  GeoJSONGeometry,
  GeoJSONProperties,
  GeoJSONFeature,
  GeoJSONFeatureCollection,
  ParcelGeometry,
  ParcelProperties,
  ParcelFeature,
  ParcelFeatureCollection,
} from './geojson.js';

// Filter types
export type {
  BaseFilter,
  FilterOperator,
  StringFilter,
  NumberFilter,
  BooleanFilter,
  DateFilter,
  GeospatialFilter,
  FilterGroup,
  Filter,
  ParcelFilters,
  AssessmentFilters,
  UserFilters,
  FilterBuilder,
  SavedFilter,
  FilterPreset,
  FilterValidationError,
  FilterValidationResult,
  QuickFilters,
  FilterOptions,
} from './filters.js';

// Export types
export type {
  ExportFormat,
  ExportStatus,
  ExportConfig,
  ExportField,
  ExportMapping,
  CSVExportOptions,
  ExcelExportOptions,
  ExcelCellStyle,
  ExcelBorder,
  PDFExportOptions,
  PDFMapOptions,
  PDFHeaderFooter,
  PDFWatermark,
  GeoJSONExportOptions,
  ShapefileExportOptions,
  ExportJob,
  ExportError,
  ExportSchedule,
  ExportTemplate,
  BulkExportRequest,
  BulkExportResponse,
  ExportStats,
  DataTransform,
  ExportPreview,
} from './exports.js';