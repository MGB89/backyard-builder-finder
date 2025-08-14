/**
 * API model definitions for property assessment data
 */

export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: 'admin' | 'assessor' | 'viewer';
  organizationId: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
  lastLoginAt?: string;
}

export interface Organization {
  id: string;
  name: string;
  type: 'county' | 'city' | 'township' | 'state';
  jurisdiction: string;
  contactInfo: {
    address: string;
    city: string;
    state: string;
    zipCode: string;
    phone?: string;
    email?: string;
    website?: string;
  };
  settings: {
    taxRate: number;
    assessmentCycle: 'annual' | 'biennial' | 'triennial';
    fiscalYearStart: string; // MM-DD format
    allowPublicAccess: boolean;
  };
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Parcel {
  id: string;
  parcelNumber: string;
  organizationId: string;
  
  // Location information
  address: {
    street: string;
    city: string;
    state: string;
    zipCode: string;
    county?: string;
  };
  
  // Property details
  propertyType: 'residential' | 'commercial' | 'industrial' | 'agricultural' | 'vacant' | 'other';
  landUse: string;
  zoning?: string;
  
  // Physical characteristics
  landArea: number; // in square feet
  frontage?: number; // in feet
  depth?: number; // in feet
  shape?: string;
  topography?: string;
  utilities: {
    water: boolean;
    sewer: boolean;
    electric: boolean;
    gas: boolean;
    internet: boolean;
  };
  
  // Improvements
  improvements: Improvement[];
  
  // Valuation
  assessedValue: number;
  landValue: number;
  improvementValue: number;
  totalValue: number;
  
  // Assessment information
  assessmentYear: number;
  effectiveDate: string;
  assessedBy: string; // User ID
  
  // Ownership
  owner: {
    name: string;
    address: {
      street: string;
      city: string;
      state: string;
      zipCode: string;
    };
    contactInfo?: {
      phone?: string;
      email?: string;
    };
  };
  
  // Legal description
  legalDescription: string;
  subdivision?: string;
  block?: string;
  lot?: string;
  section?: string;
  township?: string;
  range?: string;
  
  // Status and metadata
  status: 'active' | 'inactive' | 'pending' | 'disputed';
  notes?: string;
  exemptions: TaxExemption[];
  
  // Timestamps
  createdAt: string;
  updatedAt: string;
  lastInspectionDate?: string;
}

export interface Improvement {
  id: string;
  type: 'building' | 'structure' | 'other';
  subtype: string; // e.g., 'single-family', 'duplex', 'garage', 'barn'
  
  // Physical characteristics
  squareFootage: number;
  stories: number;
  yearBuilt: number;
  condition: 'excellent' | 'good' | 'average' | 'fair' | 'poor';
  quality: 'luxury' | 'good' | 'average' | 'economy';
  
  // Construction details
  constructionType: string; // e.g., 'frame', 'masonry', 'steel'
  roofType?: string;
  exteriorWalls?: string;
  foundation?: string;
  
  // Features
  bedrooms?: number;
  bathrooms?: number;
  halfBaths?: number;
  garages?: number;
  carports?: number;
  fireplaces?: number;
  pools?: number;
  
  // HVAC and utilities
  heating?: string;
  cooling?: string;
  plumbing?: string;
  electrical?: string;
  
  // Valuation
  value: number;
  depreciationRate: number;
  effectiveAge: number;
  
  // Status
  isActive: boolean;
  notes?: string;
}

export interface TaxExemption {
  id: string;
  type: string; // e.g., 'homestead', 'senior', 'veteran', 'disability'
  description: string;
  exemptionAmount: number;
  exemptionPercentage?: number;
  startDate: string;
  endDate?: string;
  isActive: boolean;
  qualifications: string[];
  appliedBy: string; // User ID
  approvedBy?: string; // User ID
  approvedAt?: string;
}

export interface Assessment {
  id: string;
  parcelId: string;
  assessmentYear: number;
  
  // Valuation details
  landValue: number;
  improvementValue: number;
  totalValue: number;
  assessedValue: number; // After exemptions
  
  // Assessment method
  method: 'cost' | 'sales-comparison' | 'income' | 'hybrid';
  approach: string;
  
  // Supporting data
  comparableSales?: ComparableSale[];
  costData?: CostData;
  incomeData?: IncomeData;
  
  // Status and workflow
  status: 'draft' | 'review' | 'approved' | 'appealed' | 'final';
  assessedBy: string; // User ID
  reviewedBy?: string; // User ID
  approvedBy?: string; // User ID
  
  // Dates
  assessmentDate: string;
  effectiveDate: string;
  reviewDate?: string;
  approvalDate?: string;
  
  // Notes and documentation
  notes?: string;
  documents: AssessmentDocument[];
  
  // Timestamps
  createdAt: string;
  updatedAt: string;
}

export interface ComparableSale {
  id: string;
  parcelId: string;
  saleDate: string;
  salePrice: number;
  adjustedPrice?: number;
  adjustments: SaleAdjustment[];
  source: string;
  verification: string;
  isActive: boolean;
}

export interface SaleAdjustment {
  factor: string; // e.g., 'location', 'size', 'condition', 'date'
  adjustment: number; // positive or negative
  reason: string;
}

export interface CostData {
  replacementCost: number;
  reproductionCost: number;
  depreciation: {
    physical: number;
    functional: number;
    economic: number;
    total: number;
  };
  landValue: number;
  totalValue: number;
}

export interface IncomeData {
  grossIncome: number;
  vacancy: number;
  operatingExpenses: number;
  netIncome: number;
  capitalizationRate: number;
  value: number;
}

export interface AssessmentDocument {
  id: string;
  name: string;
  type: 'photo' | 'sketch' | 'report' | 'form' | 'other';
  url: string;
  uploadedBy: string; // User ID
  uploadedAt: string;
  description?: string;
}

export interface SearchCriteria {
  query?: string;
  parcelNumber?: string;
  address?: string;
  ownerName?: string;
  propertyType?: string[];
  valueRange?: {
    min: number;
    max: number;
  };
  yearBuiltRange?: {
    min: number;
    max: number;
  };
  squareFootageRange?: {
    min: number;
    max: number;
  };
  boundingBox?: {
    north: number;
    south: number;
    east: number;
    west: number;
  };
  organizationId?: string;
  status?: string[];
  assessmentYear?: number;
}