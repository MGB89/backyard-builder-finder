/**
 * API client for Property Assessment application
 */

import type {
  ApiResponse,
  LoginRequest,
  LoginResponse,
  RefreshTokenRequest,
  RefreshTokenResponse,
  UsersListRequest,
  UsersListResponse,
  OrganizationsListResponse,
  ParcelSearchRequest,
  ParcelSearchResponse,
  CreateParcelRequest,
  UpdateParcelRequest,
  AssessmentsListRequest,
  AssessmentsListResponse,
  CreateAssessmentRequest,
  UpdateAssessmentRequest,
  BulkUpdateRequest,
  BulkUpdateResponse,
  FileUploadRequest,
  FileUploadResponse,
  ExportRequest,
  ExportResponse,
  ExportStatusResponse,
  User,
  Organization,
  Parcel,
  Assessment,
} from '../types/index.js';

export interface ApiClientConfig {
  baseUrl: string;
  timeout?: number;
  headers?: Record<string, string>;
  retryAttempts?: number;
  retryDelay?: number;
  onUnauthorized?: () => void;
  onError?: (error: ApiError) => void;
}

export interface ApiError extends Error {
  status?: number;
  code?: string;
  details?: any;
  response?: Response;
}

export interface RequestOptions {
  timeout?: number;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  retryAttempts?: number;
}

export class ApiClient {
  private baseUrl: string;
  private timeout: number;
  private defaultHeaders: Record<string, string>;
  private retryAttempts: number;
  private retryDelay: number;
  private onUnauthorized?: () => void;
  private onError?: (error: ApiError) => void;
  private accessToken?: string;

  constructor(config: ApiClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.timeout = config.timeout ?? 30000;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      ...config.headers,
    };
    this.retryAttempts = config.retryAttempts ?? 3;
    this.retryDelay = config.retryDelay ?? 1000;
    this.onUnauthorized = config.onUnauthorized;
    this.onError = config.onError;
  }

  /**
   * Set the access token for authenticated requests
   */
  setAccessToken(token: string | null): void {
    if (token) {
      this.accessToken = token;
      this.defaultHeaders['Authorization'] = `Bearer ${token}`;
    } else {
      this.accessToken = undefined;
      delete this.defaultHeaders['Authorization'];
    }
  }

  /**
   * Get the current access token
   */
  getAccessToken(): string | undefined {
    return this.accessToken;
  }

  /**
   * Make a raw HTTP request
   */
  private async request<T = any>(
    method: string,
    endpoint: string,
    data?: any,
    options: RequestOptions = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const timeout = options.timeout ?? this.timeout;
    const retryAttempts = options.retryAttempts ?? this.retryAttempts;

    const headers = {
      ...this.defaultHeaders,
      ...options.headers,
    };

    const config: any = {
      method,
      headers,
      signal: options.signal,
    };

    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
      if (data instanceof FormData) {
        // Remove Content-Type header for FormData (browser will set it with boundary)
        delete headers['Content-Type'];
        config.body = data;
      } else {
        config.body = JSON.stringify(data);
      }
    }

    let lastError: ApiError;

    for (let attempt = 0; attempt <= retryAttempts; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        const response = await fetch(url, {
          ...config,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          const error = await this.handleErrorResponse(response);
          
          // Don't retry on client errors (4xx) except 429 (rate limit)
          if (response.status >= 400 && response.status < 500 && response.status !== 429) {
            throw error;
          }
          
          lastError = error;
          
          if (attempt < retryAttempts) {
            await this.delay(this.retryDelay * Math.pow(2, attempt));
            continue;
          }
          
          throw error;
        }

        const result = await response.json();
        return result;
      } catch (error) {
        if (error instanceof TypeError && error.message.includes('fetch')) {
          // Network error
          lastError = {
            name: 'NetworkError',
            message: 'Network request failed',
            status: 0,
          } as ApiError;
        } else if (error instanceof DOMException && error.name === 'AbortError') {
          // Request timeout
          lastError = {
            name: 'TimeoutError',
            message: 'Request timeout',
            status: 408,
          } as ApiError;
        } else {
          lastError = error as ApiError;
        }

        if (attempt < retryAttempts && this.shouldRetry(lastError)) {
          await this.delay(this.retryDelay * Math.pow(2, attempt));
          continue;
        }

        break;
      }
    }

    if (this.onError) {
      this.onError(lastError);
    }

    throw lastError;
  }

  private async handleErrorResponse(response: Response): Promise<ApiError> {
    let errorData: any;
    
    try {
      errorData = await response.json();
    } catch {
      errorData = { message: response.statusText };
    }

    const error: ApiError = {
      name: 'ApiError',
      message: errorData.error?.message || errorData.message || response.statusText,
      status: response.status,
      code: errorData.error?.code || errorData.code,
      details: errorData.error?.details || errorData.details,
      response,
    };

    // Handle unauthorized responses
    if (response.status === 401 && this.onUnauthorized) {
      this.onUnauthorized();
    }

    return error;
  }

  private shouldRetry(error: ApiError): boolean {
    if (!error.status) return true; // Network errors
    if (error.status === 408) return true; // Timeout
    if (error.status === 429) return true; // Rate limit
    if (error.status >= 500) return true; // Server errors
    return false;
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // HTTP method helpers
  async get<T = any>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('GET', endpoint, undefined, options);
  }

  async post<T = any>(endpoint: string, data?: any, options?: RequestOptions): Promise<T> {
    return this.request<T>('POST', endpoint, data, options);
  }

  async put<T = any>(endpoint: string, data?: any, options?: RequestOptions): Promise<T> {
    return this.request<T>('PUT', endpoint, data, options);
  }

  async patch<T = any>(endpoint: string, data?: any, options?: RequestOptions): Promise<T> {
    return this.request<T>('PATCH', endpoint, data, options);
  }

  async delete<T = any>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('DELETE', endpoint, undefined, options);
  }

  // Authentication endpoints
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    return this.post<LoginResponse>('/auth/login', credentials);
  }

  async refreshToken(request: RefreshTokenRequest): Promise<RefreshTokenResponse> {
    return this.post<RefreshTokenResponse>('/auth/refresh', request);
  }

  async logout(): Promise<ApiResponse> {
    return this.post<ApiResponse>('/auth/logout');
  }

  // User management endpoints
  async getUsers(params?: UsersListRequest): Promise<UsersListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
    }
    const query = searchParams.toString();
    return this.get<UsersListResponse>(`/users${query ? `?${query}` : ''}`);
  }

  async getUser(id: string): Promise<ApiResponse<User>> {
    return this.get<ApiResponse<User>>(`/users/${id}`);
  }

  async createUser(user: Omit<User, 'id' | 'createdAt' | 'updatedAt'>): Promise<ApiResponse<User>> {
    return this.post<ApiResponse<User>>('/users', user);
  }

  async updateUser(id: string, updates: Partial<User>): Promise<ApiResponse<User>> {
    return this.patch<ApiResponse<User>>(`/users/${id}`, updates);
  }

  async deleteUser(id: string): Promise<ApiResponse> {
    return this.delete<ApiResponse>(`/users/${id}`);
  }

  // Organization management endpoints
  async getOrganizations(): Promise<OrganizationsListResponse> {
    return this.get<OrganizationsListResponse>('/organizations');
  }

  async getOrganization(id: string): Promise<ApiResponse<Organization>> {
    return this.get<ApiResponse<Organization>>(`/organizations/${id}`);
  }

  async createOrganization(org: Omit<Organization, 'id' | 'createdAt' | 'updatedAt'>): Promise<ApiResponse<Organization>> {
    return this.post<ApiResponse<Organization>>('/organizations', org);
  }

  async updateOrganization(id: string, updates: Partial<Organization>): Promise<ApiResponse<Organization>> {
    return this.patch<ApiResponse<Organization>>(`/organizations/${id}`, updates);
  }

  async deleteOrganization(id: string): Promise<ApiResponse> {
    return this.delete<ApiResponse>(`/organizations/${id}`);
  }

  // Parcel management endpoints
  async searchParcels(request: ParcelSearchRequest): Promise<ParcelSearchResponse> {
    return this.post<ParcelSearchResponse>('/parcels/search', request);
  }

  async getParcel(id: string): Promise<ApiResponse<Parcel>> {
    return this.get<ApiResponse<Parcel>>(`/parcels/${id}`);
  }

  async createParcel(parcel: CreateParcelRequest): Promise<ApiResponse<Parcel>> {
    return this.post<ApiResponse<Parcel>>('/parcels', parcel);
  }

  async updateParcel(id: string, updates: UpdateParcelRequest): Promise<ApiResponse<Parcel>> {
    return this.patch<ApiResponse<Parcel>>(`/parcels/${id}`, updates);
  }

  async deleteParcel(id: string): Promise<ApiResponse> {
    return this.delete<ApiResponse>(`/parcels/${id}`);
  }

  async bulkUpdateParcels(request: BulkUpdateRequest<UpdateParcelRequest>): Promise<BulkUpdateResponse> {
    return this.post<BulkUpdateResponse>('/parcels/bulk-update', request);
  }

  // Assessment management endpoints
  async getAssessments(params?: AssessmentsListRequest): Promise<AssessmentsListResponse> {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
    }
    const query = searchParams.toString();
    return this.get<AssessmentsListResponse>(`/assessments${query ? `?${query}` : ''}`);
  }

  async getAssessment(id: string): Promise<ApiResponse<Assessment>> {
    return this.get<ApiResponse<Assessment>>(`/assessments/${id}`);
  }

  async createAssessment(assessment: CreateAssessmentRequest): Promise<ApiResponse<Assessment>> {
    return this.post<ApiResponse<Assessment>>('/assessments', assessment);
  }

  async updateAssessment(id: string, updates: UpdateAssessmentRequest): Promise<ApiResponse<Assessment>> {
    return this.patch<ApiResponse<Assessment>>(`/assessments/${id}`, updates);
  }

  async deleteAssessment(id: string): Promise<ApiResponse> {
    return this.delete<ApiResponse>(`/assessments/${id}`);
  }

  // File management endpoints
  async uploadFile(request: FileUploadRequest): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', request.file, request.name);
    formData.append('type', request.type);
    if (request.description) {
      formData.append('description', request.description);
    }

    return this.post<FileUploadResponse>('/files/upload', formData);
  }

  async downloadFile(id: string): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/files/${id}/download`, {
      headers: this.defaultHeaders,
    });

    if (!response.ok) {
      throw await this.handleErrorResponse(response);
    }

    return response.blob();
  }

  // Export endpoints
  async createExport(request: ExportRequest): Promise<ExportResponse> {
    return this.post<ExportResponse>('/exports', request);
  }

  async getExportStatus(id: string): Promise<ExportStatusResponse> {
    return this.get<ExportStatusResponse>(`/exports/${id}/status`);
  }

  async downloadExport(id: string): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/exports/${id}/download`, {
      headers: this.defaultHeaders,
    });

    if (!response.ok) {
      throw await this.handleErrorResponse(response);
    }

    return response.blob();
  }

  async cancelExport(id: string): Promise<ApiResponse> {
    return this.post<ApiResponse>(`/exports/${id}/cancel`);
  }

  // Health check endpoint
  async healthCheck(): Promise<ApiResponse> {
    return this.get<ApiResponse>('/health');
  }
}