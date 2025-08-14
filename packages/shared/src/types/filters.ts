/**
 * Filter type definitions for property assessment data
 */

// Base filter types
export interface BaseFilter {
  field: string;
  operator: FilterOperator;
  value: any;
  label?: string;
}

export type FilterOperator = 
  | 'eq'           // equals
  | 'ne'           // not equals
  | 'gt'           // greater than
  | 'gte'          // greater than or equal
  | 'lt'           // less than
  | 'lte'          // less than or equal
  | 'in'           // in array
  | 'nin'          // not in array
  | 'contains'     // contains substring
  | 'startsWith'   // starts with
  | 'endsWith'     // ends with
  | 'regex'        // regular expression
  | 'between'      // between two values
  | 'isNull'       // is null
  | 'isNotNull'    // is not null
  | 'isEmpty'      // is empty string/array
  | 'isNotEmpty'   // is not empty string/array
  | 'intersects'   // geospatial intersects
  | 'within'       // geospatial within
  | 'near'         // geospatial near
  | 'withinDistance'; // geospatial within distance

export interface StringFilter extends BaseFilter {
  operator: 'eq' | 'ne' | 'contains' | 'startsWith' | 'endsWith' | 'regex' | 'in' | 'nin' | 'isNull' | 'isNotNull' | 'isEmpty' | 'isNotEmpty';
  value: string | string[] | null;
}

export interface NumberFilter extends BaseFilter {
  operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'between' | 'in' | 'nin' | 'isNull' | 'isNotNull';
  value: number | number[] | [number, number] | null;
}

export interface BooleanFilter extends BaseFilter {
  operator: 'eq' | 'ne' | 'isNull' | 'isNotNull';
  value: boolean | null;
}

export interface DateFilter extends BaseFilter {
  operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'between' | 'isNull' | 'isNotNull';
  value: string | string[] | [string, string] | null; // ISO date strings
}

export interface GeospatialFilter extends BaseFilter {
  operator: 'intersects' | 'within' | 'contains' | 'near' | 'withinDistance';
  value: {
    geometry?: {
      type: string;
      coordinates: any[];
    };
    coordinates?: [number, number]; // [longitude, latitude]
    radius?: number; // in meters
    boundingBox?: [number, number, number, number]; // [west, south, east, north]
  };
}

// Composite filter types
export interface FilterGroup {
  operator: 'and' | 'or';
  filters: (BaseFilter | FilterGroup)[];
  label?: string;
}

export type Filter = StringFilter | NumberFilter | BooleanFilter | DateFilter | GeospatialFilter | FilterGroup;

// Predefined filter sets for different data types
export interface ParcelFilters {
  parcelNumber?: StringFilter;
  address?: StringFilter;
  ownerName?: StringFilter;
  propertyType?: StringFilter;
  landUse?: StringFilter;
  zoning?: StringFilter;
  assessedValue?: NumberFilter;
  landValue?: NumberFilter;
  improvementValue?: NumberFilter;
  totalValue?: NumberFilter;
  landArea?: NumberFilter;
  squareFootage?: NumberFilter;
  yearBuilt?: NumberFilter;
  assessmentYear?: NumberFilter;
  status?: StringFilter;
  createdAt?: DateFilter;
  updatedAt?: DateFilter;
  lastInspectionDate?: DateFilter;
  location?: GeospatialFilter;
}

export interface AssessmentFilters {
  parcelId?: StringFilter;
  assessmentYear?: NumberFilter;
  landValue?: NumberFilter;
  improvementValue?: NumberFilter;
  totalValue?: NumberFilter;
  assessedValue?: NumberFilter;
  method?: StringFilter;
  approach?: StringFilter;
  status?: StringFilter;
  assessedBy?: StringFilter;
  reviewedBy?: StringFilter;
  approvedBy?: StringFilter;
  assessmentDate?: DateFilter;
  effectiveDate?: DateFilter;
  reviewDate?: DateFilter;
  approvalDate?: DateFilter;
  createdAt?: DateFilter;
  updatedAt?: DateFilter;
}

export interface UserFilters {
  email?: StringFilter;
  firstName?: StringFilter;
  lastName?: StringFilter;
  role?: StringFilter;
  organizationId?: StringFilter;
  isActive?: BooleanFilter;
  createdAt?: DateFilter;
  updatedAt?: DateFilter;
  lastLoginAt?: DateFilter;
}

// Filter builder utilities
export interface FilterBuilder {
  field: string;
  eq(value: any): BaseFilter;
  ne(value: any): BaseFilter;
  gt(value: number): NumberFilter;
  gte(value: number): NumberFilter;
  lt(value: number): NumberFilter;
  lte(value: number): NumberFilter;
  between(min: number, max: number): NumberFilter;
  in(values: any[]): BaseFilter;
  nin(values: any[]): BaseFilter;
  contains(value: string): StringFilter;
  startsWith(value: string): StringFilter;
  endsWith(value: string): StringFilter;
  regex(pattern: string): StringFilter;
  isNull(): BaseFilter;
  isNotNull(): BaseFilter;
  isEmpty(): BaseFilter;
  isNotEmpty(): BaseFilter;
  near(coordinates: [number, number], radius: number): GeospatialFilter;
  within(geometry: { type: string; coordinates: any[] }): GeospatialFilter;
  intersects(geometry: { type: string; coordinates: any[] }): GeospatialFilter;
}

// Saved filter definitions
export interface SavedFilter {
  id: string;
  name: string;
  description?: string;
  filters: Filter[];
  isPublic: boolean;
  createdBy: string;
  organizationId: string;
  tags: string[];
  createdAt: string;
  updatedAt: string;
  usageCount: number;
  lastUsedAt?: string;
}

export interface FilterPreset {
  id: string;
  name: string;
  description?: string;
  category: 'parcel' | 'assessment' | 'user' | 'organization' | 'custom';
  filters: Filter[];
  isSystem: boolean;
  isDefault?: boolean;
  displayOrder: number;
}

// Filter validation
export interface FilterValidationError {
  field: string;
  operator: FilterOperator;
  value: any;
  error: string;
  code: string;
}

export interface FilterValidationResult {
  isValid: boolean;
  errors: FilterValidationError[];
  warnings?: string[];
}

// Quick filter types for common searches
export interface QuickFilters {
  recentlyUpdated: DateFilter;
  highValue: NumberFilter;
  newConstruction: NumberFilter;
  pendingAssessment: StringFilter;
  commercialProperties: StringFilter;
  residentialProperties: StringFilter;
  vacantLand: StringFilter;
  exemptProperties: BooleanFilter;
  largeProperties: NumberFilter;
  smallProperties: NumberFilter;
}

// Advanced filter options
export interface FilterOptions {
  caseSensitive?: boolean;
  includeInactive?: boolean;
  exactMatch?: boolean;
  fuzzySearch?: boolean;
  similarityThreshold?: number;
  maxResults?: number;
  aggregateResults?: boolean;
  groupBy?: string[];
}