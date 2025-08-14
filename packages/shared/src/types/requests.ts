/**
 * API request and response type definitions
 */

import { SearchCriteria, User, Organization, Parcel, Assessment } from './api.js';
import { ParcelFeatureCollection } from './geojson.js';

// Base types
export interface PaginationParams {
  page?: number;
  limit?: number;
  offset?: number;
}

export interface SortParams {
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  meta?: {
    timestamp: string;
    requestId: string;
    version: string;
  };
}

export interface PaginatedResponse<T = any> extends ApiResponse<T> {
  pagination?: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

// Authentication requests
export interface LoginRequest {
  email: string;
  password: string;
  organizationId?: string;
}

export interface LoginResponse extends ApiResponse {
  data: {
    user: User;
    token: string;
    refreshToken: string;
    expiresAt: string;
  };
}

export interface RefreshTokenRequest {
  refreshToken: string;
}

export interface RefreshTokenResponse extends ApiResponse {
  data: {
    token: string;
    expiresAt: string;
  };
}

// User management requests
export interface CreateUserRequest {
  email: string;
  firstName: string;
  lastName: string;
  role: User['role'];
  organizationId: string;
  password: string;
}

export interface UpdateUserRequest {
  firstName?: string;
  lastName?: string;
  role?: User['role'];
  isActive?: boolean;
}

export interface UsersListRequest extends PaginationParams, SortParams {
  organizationId?: string;
  role?: User['role'];
  isActive?: boolean;
  search?: string;
}

export type UsersListResponse = PaginatedResponse<User[]>;

// Organization management requests
export interface CreateOrganizationRequest {
  name: string;
  type: Organization['type'];
  jurisdiction: string;
  contactInfo: Organization['contactInfo'];
  settings: Organization['settings'];
}

export interface UpdateOrganizationRequest {
  name?: string;
  contactInfo?: Partial<Organization['contactInfo']>;
  settings?: Partial<Organization['settings']>;
  isActive?: boolean;
}

export type OrganizationsListResponse = PaginatedResponse<Organization[]>;

// Parcel search and management requests
export interface ParcelSearchRequest extends PaginationParams, SortParams {
  criteria: SearchCriteria;
  includeGeometry?: boolean;
  format?: 'json' | 'geojson';
}

export interface ParcelSearchResponse extends PaginatedResponse {
  data: Parcel[] | ParcelFeatureCollection;
}

export interface CreateParcelRequest {
  parcelNumber: string;
  organizationId: string;
  address: Parcel['address'];
  propertyType: Parcel['propertyType'];
  landUse: string;
  zoning?: string;
  landArea: number;
  frontage?: number;
  depth?: number;
  shape?: string;
  topography?: string;
  utilities: Parcel['utilities'];
  improvements?: Omit<Parcel['improvements'][0], 'id'>[];
  owner: Parcel['owner'];
  legalDescription: string;
  subdivision?: string;
  block?: string;
  lot?: string;
  section?: string;
  township?: string;
  range?: string;
  notes?: string;
}

export interface UpdateParcelRequest {
  address?: Partial<Parcel['address']>;
  propertyType?: Parcel['propertyType'];
  landUse?: string;
  zoning?: string;
  landArea?: number;
  frontage?: number;
  depth?: number;
  shape?: string;
  topography?: string;
  utilities?: Partial<Parcel['utilities']>;
  owner?: Partial<Parcel['owner']>;
  legalDescription?: string;
  subdivision?: string;
  block?: string;
  lot?: string;
  section?: string;
  township?: string;
  range?: string;
  status?: Parcel['status'];
  notes?: string;
}

// Assessment requests
export interface CreateAssessmentRequest {
  parcelId: string;
  assessmentYear: number;
  landValue: number;
  improvementValue: number;
  totalValue: number;
  method: Assessment['method'];
  approach: string;
  assessmentDate: string;
  effectiveDate: string;
  notes?: string;
}

export interface UpdateAssessmentRequest {
  landValue?: number;
  improvementValue?: number;
  totalValue?: number;
  method?: Assessment['method'];
  approach?: string;
  status?: Assessment['status'];
  assessmentDate?: string;
  effectiveDate?: string;
  reviewDate?: string;
  approvalDate?: string;
  notes?: string;
}

export interface AssessmentsListRequest extends PaginationParams, SortParams {
  parcelId?: string;
  assessmentYear?: number;
  status?: Assessment['status'];
  method?: Assessment['method'];
  assessedBy?: string;
  startDate?: string;
  endDate?: string;
}

export type AssessmentsListResponse = PaginatedResponse<Assessment[]>;

// Bulk operations
export interface BulkUpdateRequest<T = any> {
  ids: string[];
  updates: T;
  validateOnly?: boolean;
}

export interface BulkUpdateResponse extends ApiResponse {
  data: {
    updated: number;
    failed: number;
    errors?: Array<{
      id: string;
      error: string;
    }>;
  };
}

// File upload requests
export interface FileUploadRequest {
  file: File | Blob;
  name: string;
  type: string;
  description?: string;
}

export interface FileUploadResponse extends ApiResponse {
  data: {
    id: string;
    url: string;
    name: string;
    size: number;
    uploadedAt: string;
  };
}

// Export requests
export interface ExportRequest {
  format: 'csv' | 'xlsx' | 'pdf' | 'geojson' | 'shapefile';
  criteria?: SearchCriteria;
  fields?: string[];
  includeGeometry?: boolean;
  templateId?: string;
}

export interface ExportResponse extends ApiResponse {
  data: {
    exportId: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    downloadUrl?: string;
    expiresAt?: string;
    fileSize?: number;
    recordCount?: number;
  };
}

export interface ExportStatusResponse extends ApiResponse {
  data: {
    exportId: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress?: number;
    downloadUrl?: string;
    expiresAt?: string;
    fileSize?: number;
    recordCount?: number;
    error?: string;
  };
}