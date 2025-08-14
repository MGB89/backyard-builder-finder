// Geocode provider interface
export interface GeocodeProvider {
  geocode(address: string): Promise<{ lat: number; lng: number }>;
  reverseGeocode(lat: number, lng: number): Promise<string>;
}

// Google Maps implementation stub
export class GoogleMapsGeocoder implements GeocodeProvider {
  async geocode(address: string): Promise<{ lat: number; lng: number }> {
    // Stub implementation
    return { lat: 0, lng: 0 };
  }

  async reverseGeocode(lat: number, lng: number): Promise<string> {
    // Stub implementation
    return '';
  }
}

// Mapbox implementation stub  
export class MapboxGeocoder implements GeocodeProvider {
  async geocode(address: string): Promise<{ lat: number; lng: number }> {
    // Stub implementation
    return { lat: 0, lng: 0 };
  }

  async reverseGeocode(lat: number, lng: number): Promise<string> {
    // Stub implementation
    return '';
  }
}

export function getGeocodeProvider(provider: string): GeocodeProvider {
  switch (provider) {
    case 'google':
      return new GoogleMapsGeocoder();
    case 'mapbox':
      return new MapboxGeocoder();
    default:
      throw new Error(`Unknown geocode provider: ${provider}`);
  }
}