/**
 * GeoJSON type definitions for property assessment data
 */

export interface GeoJSONPosition {
  0: number; // longitude
  1: number; // latitude
  2?: number; // elevation (optional)
}

export interface GeoJSONGeometry {
  type: 'Point' | 'LineString' | 'Polygon' | 'MultiPoint' | 'MultiLineString' | 'MultiPolygon';
  coordinates: GeoJSONPosition | GeoJSONPosition[] | GeoJSONPosition[][] | GeoJSONPosition[][][];
}

export interface GeoJSONProperties {
  [key: string]: any;
}

export interface GeoJSONFeature<T = GeoJSONProperties> {
  type: 'Feature';
  geometry: GeoJSONGeometry | null;
  properties: T;
  id?: string | number;
}

export interface GeoJSONFeatureCollection<T = GeoJSONProperties> {
  type: 'FeatureCollection';
  features: GeoJSONFeature<T>[];
}

// Property-specific GeoJSON types
export interface ParcelGeometry extends GeoJSONGeometry {
  type: 'Polygon' | 'MultiPolygon';
}

export interface ParcelProperties extends GeoJSONProperties {
  parcelId: string;
  address?: string;
  assessedValue?: number;
  landValue?: number;
  improvementValue?: number;
  taxAmount?: number;
  yearBuilt?: number;
  squareFootage?: number;
  lotSize?: number;
  propertyType?: string;
  ownerName?: string;
  lastUpdated?: string;
}

export interface ParcelFeature extends GeoJSONFeature<ParcelProperties> {
  geometry: ParcelGeometry;
}

export interface ParcelFeatureCollection extends GeoJSONFeatureCollection<ParcelProperties> {
  features: ParcelFeature[];
}