/**
 * Export type definitions for property assessment data
 */

// Export format types
export type ExportFormat = 'csv' | 'xlsx' | 'pdf' | 'geojson' | 'shapefile' | 'kml' | 'xml' | 'json';

export type ExportStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled' | 'expired';

// Base export configuration
export interface ExportConfig {
  format: ExportFormat;
  name?: string;
  description?: string;
  includeHeaders?: boolean;
  includeGeometry?: boolean;
  coordinateSystem?: string; // e.g., 'EPSG:4326', 'EPSG:3857'
  encoding?: string; // e.g., 'UTF-8', 'ASCII'
  compression?: 'none' | 'zip' | 'gzip';
  maxRecords?: number;
  chunkSize?: number;
}

// Field selection and formatting
export interface ExportField {
  name: string;
  label?: string;
  type: 'string' | 'number' | 'boolean' | 'date' | 'geometry' | 'json';
  format?: string; // e.g., 'currency', 'percentage', 'date:YYYY-MM-DD'
  precision?: number; // for numbers
  required?: boolean;
  defaultValue?: any;
  transform?: string; // transformation function name
}

export interface ExportMapping {
  sourceField: string;
  targetField: string;
  transform?: (value: any) => any;
  format?: string;
  label?: string;
}

// CSV-specific options
export interface CSVExportOptions extends ExportConfig {
  format: 'csv';
  delimiter?: string; // default: ','
  quote?: string; // default: '"'
  escape?: string; // default: '"'
  lineTerminator?: string; // default: '\n'
  includeByteOrderMark?: boolean;
}

// Excel-specific options
export interface ExcelExportOptions extends ExportConfig {
  format: 'xlsx';
  worksheetName?: string;
  includeFilters?: boolean;
  includePivotTable?: boolean;
  autoFitColumns?: boolean;
  freezeHeaders?: boolean;
  formatting?: {
    headerStyle?: ExcelCellStyle;
    dataStyle?: ExcelCellStyle;
    alternateRowStyle?: ExcelCellStyle;
  };
}

export interface ExcelCellStyle {
  font?: {
    name?: string;
    size?: number;
    bold?: boolean;
    italic?: boolean;
    color?: string;
  };
  fill?: {
    type?: 'solid' | 'gradient';
    fgColor?: string;
    bgColor?: string;
  };
  border?: {
    top?: ExcelBorder;
    bottom?: ExcelBorder;
    left?: ExcelBorder;
    right?: ExcelBorder;
  };
  alignment?: {
    horizontal?: 'left' | 'center' | 'right';
    vertical?: 'top' | 'middle' | 'bottom';
    wrapText?: boolean;
  };
  numberFormat?: string;
}

export interface ExcelBorder {
  style: 'thin' | 'medium' | 'thick' | 'dotted' | 'dashed';
  color?: string;
}

// PDF-specific options
export interface PDFExportOptions extends ExportConfig {
  format: 'pdf';
  template: 'table' | 'report' | 'summary' | 'map' | 'custom';
  templateId?: string;
  orientation?: 'portrait' | 'landscape';
  pageSize?: 'A4' | 'Letter' | 'Legal' | 'A3' | 'Tabloid';
  margins?: {
    top: number;
    bottom: number;
    left: number;
    right: number;
  };
  includeMap?: boolean;
  mapOptions?: PDFMapOptions;
  header?: PDFHeaderFooter;
  footer?: PDFHeaderFooter;
  watermark?: PDFWatermark;
}

export interface PDFMapOptions {
  center?: [number, number]; // [longitude, latitude]
  zoom?: number;
  width?: number;
  height?: number;
  showScale?: boolean;
  showNorthArrow?: boolean;
  layers?: string[];
}

export interface PDFHeaderFooter {
  text?: string;
  includeDate?: boolean;
  includePageNumbers?: boolean;
  includeOrganizationInfo?: boolean;
  customFields?: Record<string, any>;
}

export interface PDFWatermark {
  text: string;
  opacity?: number;
  angle?: number;
  color?: string;
  fontSize?: number;
}

// GeoJSON-specific options
export interface GeoJSONExportOptions extends ExportConfig {
  format: 'geojson';
  precision?: number; // decimal places for coordinates
  includeNullGeometry?: boolean;
  geometryType?: 'Point' | 'LineString' | 'Polygon' | 'MultiPoint' | 'MultiLineString' | 'MultiPolygon';
  simplifyGeometry?: number; // tolerance for simplification
}

// Shapefile-specific options
export interface ShapefileExportOptions extends ExportConfig {
  format: 'shapefile';
  geometryType: 'Point' | 'LineString' | 'Polygon' | 'MultiPoint' | 'MultiLineString' | 'MultiPolygon';
  includeProjectionFile?: boolean;
  fieldNameMapping?: Record<string, string>; // handle field name limitations
  maxFieldLength?: number; // default: 10 (DBF limitation)
}

// Export job definition
export interface ExportJob {
  id: string;
  name: string;
  description?: string;
  organizationId: string;
  createdBy: string;
  
  // Configuration
  config: ExportConfig;
  fields: ExportField[];
  filters?: any[]; // search criteria/filters
  mappings?: ExportMapping[];
  
  // Status and progress
  status: ExportStatus;
  progress?: number; // 0-100
  recordCount?: number;
  processedCount?: number;
  errorCount?: number;
  
  // Results
  downloadUrl?: string;
  fileName?: string;
  fileSize?: number;
  checksum?: string;
  expiresAt?: string;
  
  // Execution details
  startedAt?: string;
  completedAt?: string;
  estimatedDuration?: number; // in seconds
  actualDuration?: number; // in seconds
  
  // Error handling
  errors?: ExportError[];
  warnings?: string[];
  
  // Metadata
  createdAt: string;
  updatedAt: string;
  tags?: string[];
  isRecurring?: boolean;
  schedule?: ExportSchedule;
}

export interface ExportError {
  type: 'validation' | 'processing' | 'system' | 'timeout' | 'permission';
  code: string;
  message: string;
  details?: any;
  recordId?: string;
  field?: string;
  lineNumber?: number;
  timestamp: string;
}

// Scheduled exports
export interface ExportSchedule {
  id: string;
  name: string;
  isEnabled: boolean;
  cronExpression: string; // e.g., '0 0 * * 1' for weekly on Monday
  timezone: string;
  lastRun?: string;
  nextRun?: string;
  runCount: number;
  failureCount: number;
  
  // Notification settings
  notifications?: {
    onSuccess?: boolean;
    onFailure?: boolean;
    recipients: string[];
    template?: string;
  };
  
  // Retention policy
  retention?: {
    keepCount?: number; // number of exports to keep
    keepDays?: number; // days to keep exports
    deleteAfterDownload?: boolean;
  };
}

// Export templates
export interface ExportTemplate {
  id: string;
  name: string;
  description?: string;
  category: 'parcel' | 'assessment' | 'reporting' | 'analysis' | 'custom';
  
  // Template configuration
  config: ExportConfig;
  fields: ExportField[];
  defaultFilters?: any[];
  mappings?: ExportMapping[];
  
  // Access control
  isPublic: boolean;
  isSystem: boolean;
  organizationId?: string;
  createdBy: string;
  
  // Usage tracking
  usageCount: number;
  lastUsedAt?: string;
  rating?: number;
  
  // Metadata
  tags: string[];
  version: string;
  createdAt: string;
  updatedAt: string;
}

// Bulk export operations
export interface BulkExportRequest {
  jobs: Omit<ExportJob, 'id' | 'status' | 'createdAt' | 'updatedAt'>[];
  executeInParallel?: boolean;
  maxConcurrentJobs?: number;
  notificationEmail?: string;
}

export interface BulkExportResponse {
  batchId: string;
  jobIds: string[];
  totalJobs: number;
  estimatedDuration?: number;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  createdAt: string;
}

// Export analytics and statistics
export interface ExportStats {
  organizationId: string;
  period: 'day' | 'week' | 'month' | 'year';
  startDate: string;
  endDate: string;
  
  totalExports: number;
  successfulExports: number;
  failedExports: number;
  averageDuration: number;
  totalDataExported: number; // in bytes
  totalRecordsExported: number;
  
  byFormat: Record<ExportFormat, {
    count: number;
    totalSize: number;
    averageDuration: number;
  }>;
  
  byUser: Record<string, {
    count: number;
    totalSize: number;
    lastExport: string;
  }>;
  
  popularTemplates: Array<{
    templateId: string;
    templateName: string;
    usageCount: number;
  }>;
  
  peakUsageHours: number[];
  errors: Record<string, number>; // error code to count mapping
}

// Import/export utilities
export interface DataTransform {
  type: 'format' | 'calculate' | 'lookup' | 'combine' | 'split' | 'custom';
  name: string;
  description?: string;
  parameters?: Record<string, any>;
  function?: string; // for custom transforms
}

export interface ExportPreview {
  headers: string[];
  sampleRows: any[][];
  totalRows: number;
  estimatedFileSize: number;
  validationErrors?: ExportError[];
  warnings?: string[];
}