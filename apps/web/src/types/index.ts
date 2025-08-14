// Common types used throughout the application

export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  role: 'admin' | 'assessor' | 'user';
  createdAt: Date;
  updatedAt: Date;
}

export interface Property {
  id: string;
  address: string;
  city: string;
  state: string;
  zipCode: string;
  latitude: number;
  longitude: number;
  propertyType: 'residential' | 'commercial' | 'industrial' | 'land';
  bedrooms?: number;
  bathrooms?: number;
  squareFootage?: number;
  lotSize?: number;
  yearBuilt?: number;
  assessedValue?: number;
  marketValue?: number;
  taxAmount?: number;
  lastAssessmentDate?: Date;
  createdAt: Date;
  updatedAt: Date;
}

export interface Assessment {
  id: string;
  propertyId: string;
  assessorId: string;
  assessmentType: 'initial' | 'reassessment' | 'appeal';
  status: 'pending' | 'in_progress' | 'completed' | 'reviewed';
  assessedValue: number;
  marketValue: number;
  methodology: string;
  notes?: string;
  documents: AssessmentDocument[];
  completedAt?: Date;
  createdAt: Date;
  updatedAt: Date;
}

export interface AssessmentDocument {
  id: string;
  assessmentId: string;
  filename: string;
  fileType: string;
  fileSize: number;
  url: string;
  description?: string;
  uploadedAt: Date;
}

export interface MapLocation {
  latitude: number;
  longitude: number;
  zoom?: number;
}

export interface SearchFilters {
  city?: string;
  state?: string;
  propertyType?: Property['propertyType'];
  minValue?: number;
  maxValue?: number;
  minSquareFootage?: number;
  maxSquareFootage?: number;
  minBedrooms?: number;
  maxBedrooms?: number;
  minBathrooms?: number;
  maxBathrooms?: number;
  yearBuiltMin?: number;
  yearBuiltMax?: number;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
  pagination?: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

export interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, any>;
}

// Form types
export interface LoginForm {
  email: string;
  password: string;
}

export interface RegisterForm {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

export interface PropertyForm {
  address: string;
  city: string;
  state: string;
  zipCode: string;
  propertyType: Property['propertyType'];
  bedrooms?: number;
  bathrooms?: number;
  squareFootage?: number;
  lotSize?: number;
  yearBuilt?: number;
}

export interface AssessmentForm {
  propertyId: string;
  assessmentType: Assessment['assessmentType'];
  assessedValue: number;
  marketValue: number;
  methodology: string;
  notes?: string;
}

// Utility types
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>;