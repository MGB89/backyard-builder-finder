/**
 * Validation utilities for property assessment data
 */

import type { Parcel, Assessment, User, Organization } from '../types/index.js';

export interface ValidationError {
  field: string;
  message: string;
  code: string;
  value?: any;
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
  warnings?: string[];
}

// Regular expressions for common validations
const PATTERNS = {
  email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  phone: /^\+?[\d\s\-().]$/,
  zipCode: /^\d{5}(-\d{4})?$/,
  parcelNumber: /^[A-Z0-9-]+$/i,
  coordinates: /^-?\d+\.?\d*$/,
} as const;

// Common validation functions
export function isRequired(value: any, fieldName: string): ValidationError | null {
  if (value === undefined || value === null || value === '') {
    return {
      field: fieldName,
      message: `${fieldName} is required`,
      code: 'REQUIRED',
      value,
    };
  }
  return null;
}

export function isEmail(value: string, fieldName: string): ValidationError | null {
  if (value && !PATTERNS.email.test(value)) {
    return {
      field: fieldName,
      message: `${fieldName} must be a valid email address`,
      code: 'INVALID_EMAIL',
      value,
    };
  }
  return null;
}

export function isPhone(value: string, fieldName: string): ValidationError | null {
  if (value && !PATTERNS.phone.test(value)) {
    return {
      field: fieldName,
      message: `${fieldName} must be a valid phone number`,
      code: 'INVALID_PHONE',
      value,
    };
  }
  return null;
}

export function isZipCode(value: string, fieldName: string): ValidationError | null {
  if (value && !PATTERNS.zipCode.test(value)) {
    return {
      field: fieldName,
      message: `${fieldName} must be a valid zip code (12345 or 12345-6789)`,
      code: 'INVALID_ZIP_CODE',
      value,
    };
  }
  return null;
}

export function isPositiveNumber(value: number, fieldName: string): ValidationError | null {
  if (typeof value === 'number' && value < 0) {
    return {
      field: fieldName,
      message: `${fieldName} must be a positive number`,
      code: 'INVALID_POSITIVE_NUMBER',
      value,
    };
  }
  return null;
}

export function isInRange(value: number, min: number, max: number, fieldName: string): ValidationError | null {
  if (typeof value === 'number' && (value < min || value > max)) {
    return {
      field: fieldName,
      message: `${fieldName} must be between ${min} and ${max}`,
      code: 'OUT_OF_RANGE',
      value,
    };
  }
  return null;
}

export function isValidDate(value: string, fieldName: string): ValidationError | null {
  if (value && isNaN(Date.parse(value))) {
    return {
      field: fieldName,
      message: `${fieldName} must be a valid date`,
      code: 'INVALID_DATE',
      value,
    };
  }
  return null;
}

export function isValidYear(value: number, fieldName: string): ValidationError | null {
  const currentYear = new Date().getFullYear();
  if (typeof value === 'number' && (value < 1800 || value > currentYear + 10)) {
    return {
      field: fieldName,
      message: `${fieldName} must be a valid year between 1800 and ${currentYear + 10}`,
      code: 'INVALID_YEAR',
      value,
    };
  }
  return null;
}

export function isValidCoordinate(value: number, type: 'latitude' | 'longitude', fieldName: string): ValidationError | null {
  if (typeof value !== 'number') {
    return {
      field: fieldName,
      message: `${fieldName} must be a number`,
      code: 'INVALID_COORDINATE_TYPE',
      value,
    };
  }

  const bounds = type === 'latitude' ? [-90, 90] : [-180, 180];
  if (value < bounds[0] || value > bounds[1]) {
    return {
      field: fieldName,
      message: `${fieldName} must be between ${bounds[0]} and ${bounds[1]}`,
      code: 'INVALID_COORDINATE_RANGE',
      value,
    };
  }

  return null;
}

// Entity-specific validation functions
export function validateUser(user: Partial<User>): ValidationResult {
  const errors: ValidationError[] = [];

  // Required fields
  const requiredFields = ['email', 'firstName', 'lastName', 'role', 'organizationId'];
  requiredFields.forEach(field => {
    const error = isRequired(user[field as keyof User], field);
    if (error) errors.push(error);
  });

  // Email validation
  if (user.email) {
    const emailError = isEmail(user.email, 'email');
    if (emailError) errors.push(emailError);
  }

  // Role validation
  if (user.role && !['admin', 'assessor', 'viewer'].includes(user.role)) {
    errors.push({
      field: 'role',
      message: 'Role must be one of: admin, assessor, viewer',
      code: 'INVALID_ROLE',
      value: user.role,
    });
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

export function validateOrganization(org: Partial<Organization>): ValidationResult {
  const errors: ValidationError[] = [];

  // Required fields
  const requiredFields = ['name', 'type', 'jurisdiction'];
  requiredFields.forEach(field => {
    const error = isRequired(org[field as keyof Organization], field);
    if (error) errors.push(error);
  });

  // Type validation
  if (org.type && !['county', 'city', 'township', 'state'].includes(org.type)) {
    errors.push({
      field: 'type',
      message: 'Type must be one of: county, city, township, state',
      code: 'INVALID_ORGANIZATION_TYPE',
      value: org.type,
    });
  }

  // Contact info validation
  if (org.contactInfo) {
    const contactInfo = org.contactInfo;
    const { address, city, state, zipCode, phone, email } = contactInfo;
    
    if (address) {
      const addressError = isRequired(address, 'contactInfo.address');
      if (addressError) errors.push(addressError);
    }
    
    if (city) {
      const cityError = isRequired(city, 'contactInfo.city');
      if (cityError) errors.push(cityError);
    }
    
    if (state) {
      const stateError = isRequired(state, 'contactInfo.state');
      if (stateError) errors.push(stateError);
    }
    
    if (zipCode) {
      const zipError = isZipCode(zipCode, 'contactInfo.zipCode');
      if (zipError) errors.push(zipError);
    }
    
    if (phone) {
      const phoneError = isPhone(phone, 'contactInfo.phone');
      if (phoneError) errors.push(phoneError);
    }
    
    if (email) {
      const emailError = isEmail(email, 'contactInfo.email');
      if (emailError) errors.push(emailError);
    }
  }

  // Settings validation
  if (org.settings) {
    const { taxRate, assessmentCycle } = org.settings;
    
    if (taxRate !== undefined) {
      const taxRateError = isPositiveNumber(taxRate, 'settings.taxRate');
      if (taxRateError) errors.push(taxRateError);
      
      const rangeError = isInRange(taxRate, 0, 100, 'settings.taxRate');
      if (rangeError) errors.push(rangeError);
    }
    
    if (assessmentCycle && !['annual', 'biennial', 'triennial'].includes(assessmentCycle)) {
      errors.push({
        field: 'settings.assessmentCycle',
        message: 'Assessment cycle must be one of: annual, biennial, triennial',
        code: 'INVALID_ASSESSMENT_CYCLE',
        value: assessmentCycle,
      });
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

export function validateParcel(parcel: Partial<Parcel>): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: string[] = [];

  // Required fields
  const requiredFields = ['parcelNumber', 'organizationId', 'address', 'propertyType', 'landUse', 'landArea'];
  requiredFields.forEach(field => {
    const error = isRequired(parcel[field as keyof Parcel], field);
    if (error) errors.push(error);
  });

  // Parcel number validation
  if (parcel.parcelNumber && !PATTERNS.parcelNumber.test(parcel.parcelNumber)) {
    errors.push({
      field: 'parcelNumber',
      message: 'Parcel number must contain only letters, numbers, and hyphens',
      code: 'INVALID_PARCEL_NUMBER',
      value: parcel.parcelNumber,
    });
  }

  // Property type validation
  const validPropertyTypes = ['residential', 'commercial', 'industrial', 'agricultural', 'vacant', 'other'];
  if (parcel.propertyType && !validPropertyTypes.includes(parcel.propertyType)) {
    errors.push({
      field: 'propertyType',
      message: `Property type must be one of: ${validPropertyTypes.join(', ')}`,
      code: 'INVALID_PROPERTY_TYPE',
      value: parcel.propertyType,
    });
  }

  // Address validation
  if (parcel.address) {
    const { street, city, state, zipCode } = parcel.address;
    
    const streetError = isRequired(street, 'address.street');
    if (streetError) errors.push(streetError);
    
    const cityError = isRequired(city, 'address.city');
    if (cityError) errors.push(cityError);
    
    const stateError = isRequired(state, 'address.state');
    if (stateError) errors.push(stateError);
    
    const zipError = isRequired(zipCode, 'address.zipCode');
    if (zipError) errors.push(zipError);
    else {
      const zipFormatError = isZipCode(zipCode, 'address.zipCode');
      if (zipFormatError) errors.push(zipFormatError);
    }
  }

  // Numeric field validations
  if (parcel.landArea !== undefined) {
    const landAreaError = isPositiveNumber(parcel.landArea, 'landArea');
    if (landAreaError) errors.push(landAreaError);
  }

  if (parcel.frontage !== undefined) {
    const frontageError = isPositiveNumber(parcel.frontage, 'frontage');
    if (frontageError) errors.push(frontageError);
  }

  if (parcel.depth !== undefined) {
    const depthError = isPositiveNumber(parcel.depth, 'depth');
    if (depthError) errors.push(depthError);
  }

  // Value validations
  if (parcel.assessedValue !== undefined) {
    const assessedValueError = isPositiveNumber(parcel.assessedValue, 'assessedValue');
    if (assessedValueError) errors.push(assessedValueError);
  }

  if (parcel.landValue !== undefined) {
    const landValueError = isPositiveNumber(parcel.landValue, 'landValue');
    if (landValueError) errors.push(landValueError);
  }

  if (parcel.improvementValue !== undefined) {
    const improvementValueError = isPositiveNumber(parcel.improvementValue, 'improvementValue');
    if (improvementValueError) errors.push(improvementValueError);
  }

  if (parcel.totalValue !== undefined) {
    const totalValueError = isPositiveNumber(parcel.totalValue, 'totalValue');
    if (totalValueError) errors.push(totalValueError);
  }

  // Assessment year validation
  if (parcel.assessmentYear !== undefined) {
    const yearError = isValidYear(parcel.assessmentYear, 'assessmentYear');
    if (yearError) errors.push(yearError);
  }

  // Status validation
  const validStatuses = ['active', 'inactive', 'pending', 'disputed'];
  if (parcel.status && !validStatuses.includes(parcel.status)) {
    errors.push({
      field: 'status',
      message: `Status must be one of: ${validStatuses.join(', ')}`,
      code: 'INVALID_STATUS',
      value: parcel.status,
    });
  }

  // Owner validation
  if (parcel.owner) {
    const ownerNameError = isRequired(parcel.owner.name, 'owner.name');
    if (ownerNameError) errors.push(ownerNameError);

    if (parcel.owner.address) {
      const { street, city, state, zipCode } = parcel.owner.address;
      
      const ownerStreetError = isRequired(street, 'owner.address.street');
      if (ownerStreetError) errors.push(ownerStreetError);
      
      const ownerCityError = isRequired(city, 'owner.address.city');
      if (ownerCityError) errors.push(ownerCityError);
      
      const ownerStateError = isRequired(state, 'owner.address.state');
      if (ownerStateError) errors.push(ownerStateError);
      
      const ownerZipError = isRequired(zipCode, 'owner.address.zipCode');
      if (ownerZipError) errors.push(ownerZipError);
      else {
        const ownerZipFormatError = isZipCode(zipCode, 'owner.address.zipCode');
        if (ownerZipFormatError) errors.push(ownerZipFormatError);
      }
    }

    if (parcel.owner.contactInfo?.email) {
      const ownerEmailError = isEmail(parcel.owner.contactInfo.email, 'owner.contactInfo.email');
      if (ownerEmailError) errors.push(ownerEmailError);
    }

    if (parcel.owner.contactInfo?.phone) {
      const ownerPhoneError = isPhone(parcel.owner.contactInfo.phone, 'owner.contactInfo.phone');
      if (ownerPhoneError) errors.push(ownerPhoneError);
    }
  }

  // Cross-field validations and warnings
  if (parcel.landValue !== undefined && parcel.improvementValue !== undefined && parcel.totalValue !== undefined) {
    const expectedTotal = parcel.landValue + parcel.improvementValue;
    if (Math.abs(parcel.totalValue - expectedTotal) > 0.01) {
      warnings.push(`Total value (${parcel.totalValue}) does not equal land value + improvement value (${expectedTotal})`);
    }
  }

  if (parcel.improvements && parcel.improvements.length > 0) {
    let totalImprovementValue = 0;
    parcel.improvements.forEach((improvement, index) => {
      if (improvement.squareFootage !== undefined) {
        const sqftError = isPositiveNumber(improvement.squareFootage, `improvements[${index}].squareFootage`);
        if (sqftError) errors.push(sqftError);
      }

      if (improvement.yearBuilt !== undefined) {
        const yearError = isValidYear(improvement.yearBuilt, `improvements[${index}].yearBuilt`);
        if (yearError) errors.push(yearError);
      }

      if (improvement.value !== undefined) {
        const valueError = isPositiveNumber(improvement.value, `improvements[${index}].value`);
        if (valueError) errors.push(valueError);
        else {
          totalImprovementValue += improvement.value;
        }
      }
    });

    if (parcel.improvementValue && Math.abs(parcel.improvementValue - totalImprovementValue) > 0.01) {
      warnings.push(`Improvement value (${parcel.improvementValue}) does not match sum of individual improvement values (${totalImprovementValue})`);
    }
  }

  const result: ValidationResult = {
    isValid: errors.length === 0,
    errors,
  };
  
  if (warnings.length > 0) {
    result.warnings = warnings;
  }
  
  return result;
}

export function validateAssessment(assessment: Partial<Assessment>): ValidationResult {
  const errors: ValidationError[] = [];

  // Required fields
  const requiredFields = ['parcelId', 'assessmentYear', 'landValue', 'improvementValue', 'totalValue', 'method'];
  requiredFields.forEach(field => {
    const error = isRequired(assessment[field as keyof Assessment], field);
    if (error) errors.push(error);
  });

  // Assessment year validation
  if (assessment.assessmentYear !== undefined) {
    const yearError = isValidYear(assessment.assessmentYear, 'assessmentYear');
    if (yearError) errors.push(yearError);
  }

  // Value validations
  if (assessment.landValue !== undefined) {
    const landValueError = isPositiveNumber(assessment.landValue, 'landValue');
    if (landValueError) errors.push(landValueError);
  }

  if (assessment.improvementValue !== undefined) {
    const improvementValueError = isPositiveNumber(assessment.improvementValue, 'improvementValue');
    if (improvementValueError) errors.push(improvementValueError);
  }

  if (assessment.totalValue !== undefined) {
    const totalValueError = isPositiveNumber(assessment.totalValue, 'totalValue');
    if (totalValueError) errors.push(totalValueError);
  }

  if (assessment.assessedValue !== undefined) {
    const assessedValueError = isPositiveNumber(assessment.assessedValue, 'assessedValue');
    if (assessedValueError) errors.push(assessedValueError);
  }

  // Method validation
  const validMethods = ['cost', 'sales-comparison', 'income', 'hybrid'];
  if (assessment.method && !validMethods.includes(assessment.method)) {
    errors.push({
      field: 'method',
      message: `Method must be one of: ${validMethods.join(', ')}`,
      code: 'INVALID_ASSESSMENT_METHOD',
      value: assessment.method,
    });
  }

  // Status validation
  const validStatuses = ['draft', 'review', 'approved', 'appealed', 'final'];
  if (assessment.status && !validStatuses.includes(assessment.status)) {
    errors.push({
      field: 'status',
      message: `Status must be one of: ${validStatuses.join(', ')}`,
      code: 'INVALID_ASSESSMENT_STATUS',
      value: assessment.status,
    });
  }

  // Date validations
  if (assessment.assessmentDate) {
    const dateError = isValidDate(assessment.assessmentDate, 'assessmentDate');
    if (dateError) errors.push(dateError);
  }

  if (assessment.effectiveDate) {
    const dateError = isValidDate(assessment.effectiveDate, 'effectiveDate');
    if (dateError) errors.push(dateError);
  }

  if (assessment.reviewDate) {
    const dateError = isValidDate(assessment.reviewDate, 'reviewDate');
    if (dateError) errors.push(dateError);
  }

  if (assessment.approvalDate) {
    const dateError = isValidDate(assessment.approvalDate, 'approvalDate');
    if (dateError) errors.push(dateError);
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

// Batch validation function
export function validateBatch<T>(
  items: T[],
  validator: (item: T) => ValidationResult
): { valid: T[]; invalid: Array<{ item: T; errors: ValidationError[] }> } {
  const valid: T[] = [];
  const invalid: Array<{ item: T; errors: ValidationError[] }> = [];

  items.forEach(item => {
    const result = validator(item);
    if (result.isValid) {
      valid.push(item);
    } else {
      invalid.push({ item, errors: result.errors });
    }
  });

  return { valid, invalid };
}