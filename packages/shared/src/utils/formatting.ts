/**
 * Formatting utilities for property assessment data
 */

// Currency formatting
export function formatCurrency(
  amount: number,
  currency: string = 'USD',
  locale: string = 'en-US'
): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatCurrencyWithCents(
  amount: number,
  currency: string = 'USD',
  locale: string = 'en-US'
): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

// Number formatting
export function formatNumber(
  value: number,
  locale: string = 'en-US',
  options?: Intl.NumberFormatOptions
): string {
  return new Intl.NumberFormat(locale, options).format(value);
}

export function formatPercentage(
  value: number,
  locale: string = 'en-US',
  decimals: number = 1
): string {
  return new Intl.NumberFormat(locale, {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value / 100);
}

export function formatSquareFootage(squareFootage: number): string {
  return `${formatNumber(squareFootage)} sq ft`;
}

export function formatAcreage(squareFootage: number): string {
  const acres = squareFootage / 43560;
  return `${formatNumber(acres, 'en-US', { maximumFractionDigits: 2 })} acres`;
}

export function formatLandArea(squareFootage: number): string {
  if (squareFootage >= 43560) {
    return formatAcreage(squareFootage);
  }
  return formatSquareFootage(squareFootage);
}

// Date formatting
export function formatDate(
  date: string | Date,
  locale: string = 'en-US',
  options?: Intl.DateTimeFormatOptions
): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    ...options,
  }).format(dateObj);
}

export function formatDateTime(
  date: string | Date,
  locale: string = 'en-US',
  options?: Intl.DateTimeFormatOptions
): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    ...options,
  }).format(dateObj);
}

export function formatRelativeTime(date: string | Date, locale: string = 'en-US'): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - dateObj.getTime()) / 1000);

  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });

  if (diffInSeconds < 60) {
    return rtf.format(-diffInSeconds, 'second');
  } else if (diffInSeconds < 3600) {
    return rtf.format(-Math.floor(diffInSeconds / 60), 'minute');
  } else if (diffInSeconds < 86400) {
    return rtf.format(-Math.floor(diffInSeconds / 3600), 'hour');
  } else if (diffInSeconds < 2592000) {
    return rtf.format(-Math.floor(diffInSeconds / 86400), 'day');
  } else if (diffInSeconds < 31536000) {
    return rtf.format(-Math.floor(diffInSeconds / 2592000), 'month');
  } else {
    return rtf.format(-Math.floor(diffInSeconds / 31536000), 'year');
  }
}

// Address formatting
export function formatAddress(address: {
  street: string;
  city: string;
  state: string;
  zipCode: string;
  county?: string;
}): string {
  return `${address.street}, ${address.city}, ${address.state} ${address.zipCode}`;
}

export function formatFullAddress(address: {
  street: string;
  city: string;
  state: string;
  zipCode: string;
  county?: string;
}): string {
  const baseAddress = formatAddress(address);
  return address.county ? `${baseAddress} (${address.county} County)` : baseAddress;
}

// Property type formatting
export function formatPropertyType(type: string): string {
  const typeMap: Record<string, string> = {
    residential: 'Residential',
    commercial: 'Commercial',
    industrial: 'Industrial',
    agricultural: 'Agricultural',
    vacant: 'Vacant Land',
    other: 'Other',
  };

  return typeMap[type] || type;
}

// Assessment status formatting
export function formatAssessmentStatus(status: string): string {
  const statusMap: Record<string, string> = {
    draft: 'Draft',
    review: 'Under Review',
    approved: 'Approved',
    appealed: 'Under Appeal',
    final: 'Final',
  };

  return statusMap[status] || status;
}

// User role formatting
export function formatUserRole(role: string): string {
  const roleMap: Record<string, string> = {
    admin: 'Administrator',
    assessor: 'Assessor',
    viewer: 'Viewer',
  };

  return roleMap[role] || role;
}

// Organization type formatting
export function formatOrganizationType(type: string): string {
  const typeMap: Record<string, string> = {
    county: 'County',
    city: 'City',
    township: 'Township',
    state: 'State',
  };

  return typeMap[type] || type;
}

// Parcel number formatting
export function formatParcelNumber(parcelNumber: string): string {
  // Remove any existing formatting
  const cleaned = parcelNumber.replace(/[^A-Z0-9]/gi, '');
  
  // Common parcel number formats (can be customized based on jurisdiction)
  if (cleaned.length === 12) {
    // Format: 123-456-789-012
    return cleaned.replace(/(\d{3})(\d{3})(\d{3})(\d{3})/, '$1-$2-$3-$4');
  } else if (cleaned.length === 10) {
    // Format: 12-34-567-890
    return cleaned.replace(/(\d{2})(\d{2})(\d{3})(\d{3})/, '$1-$2-$3-$4');
  } else if (cleaned.length === 9) {
    // Format: 123-45-6789
    return cleaned.replace(/(\d{3})(\d{2})(\d{4})/, '$1-$2-$3');
  }
  
  return parcelNumber; // Return as-is if no standard format matches
}

// Phone number formatting
export function formatPhoneNumber(phoneNumber: string, format: 'us' | 'international' = 'us'): string {
  // Remove all non-digits
  const cleaned = phoneNumber.replace(/\D/g, '');
  
  if (format === 'us' && cleaned.length === 10) {
    // Format: (123) 456-7890
    return cleaned.replace(/(\d{3})(\d{3})(\d{4})/, '($1) $2-$3');
  } else if (format === 'us' && cleaned.length === 11 && cleaned.startsWith('1')) {
    // Format: +1 (123) 456-7890
    return cleaned.replace(/1(\d{3})(\d{3})(\d{4})/, '+1 ($1) $2-$3');
  }
  
  return phoneNumber; // Return as-is if no standard format matches
}

// Coordinate formatting
export function formatCoordinates(
  longitude: number,
  latitude: number,
  precision: number = 6
): string {
  const lat = latitude.toFixed(precision);
  const lng = longitude.toFixed(precision);
  return `${lat}, ${lng}`;
}

export function formatCoordinatesDMS(longitude: number, latitude: number): string {
  function toDMS(coordinate: number, isLatitude: boolean): string {
    const absolute = Math.abs(coordinate);
    const degrees = Math.floor(absolute);
    const minutes = Math.floor((absolute - degrees) * 60);
    const seconds = ((absolute - degrees - minutes / 60) * 3600).toFixed(2);
    
    const direction = isLatitude 
      ? (coordinate >= 0 ? 'N' : 'S')
      : (coordinate >= 0 ? 'E' : 'W');
    
    return `${degrees}°${minutes}'${seconds}"${direction}`;
  }
  
  return `${toDMS(latitude, true)}, ${toDMS(longitude, false)}`;
}

// File size formatting
export function formatFileSize(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIndex = 0;
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  
  return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

// Duration formatting
export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`;
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
  }
}

// Assessment method formatting
export function formatAssessmentMethod(method: string): string {
  const methodMap: Record<string, string> = {
    'cost': 'Cost Approach',
    'sales-comparison': 'Sales Comparison Approach',
    'income': 'Income Approach',
    'hybrid': 'Hybrid Approach',
  };

  return methodMap[method] || method;
}

// Tax exemption formatting
export function formatTaxExemption(exemption: {
  type: string;
  exemptionAmount?: number;
  exemptionPercentage?: number;
}): string {
  const { type, exemptionAmount, exemptionPercentage } = exemption;
  
  let description = type.charAt(0).toUpperCase() + type.slice(1);
  
  if (exemptionAmount) {
    description += ` (${formatCurrency(exemptionAmount)})`;
  } else if (exemptionPercentage) {
    description += ` (${formatPercentage(exemptionPercentage)}%)`;
  }
  
  return description;
}

// Search result highlighting
export function highlightSearchTerm(text: string, searchTerm: string): string {
  if (!searchTerm || !text) return text;
  
  const regex = new RegExp(`(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  return text.replace(regex, '<mark>$1</mark>');
}

// Utility function to truncate text
export function truncateText(text: string, maxLength: number, suffix: string = '...'): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - suffix.length) + suffix;
}

// Utility function to title case
export function toTitleCase(str: string): string {
  return str.replace(/\w\S*/g, (txt) => 
    txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase()
  );
}

// Utility function to format list with proper conjunction
export function formatList(items: string[], conjunction: string = 'and'): string {
  if (items.length === 0) return '';
  if (items.length === 1) return items[0];
  if (items.length === 2) return `${items[0]} ${conjunction} ${items[1]}`;
  
  return `${items.slice(0, -1).join(', ')}, ${conjunction} ${items[items.length - 1]}`;
}