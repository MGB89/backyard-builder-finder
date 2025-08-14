'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';

// Dynamically import MapLibre to avoid SSR issues
const Map = dynamic(() => import('@/components/map/demo-map'), {
  ssr: false,
  loading: () => <div className="w-full h-full bg-gray-100 animate-pulse" />
});

export default function DemoPage() {
  const [searchArea, setSearchArea] = useState('Los Angeles, CA');
  const [unitSize, setUnitSize] = useState(1200);
  const [excludePools, setExcludePools] = useState(true);
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = () => {
    setLoading(true);
    // Simulate search with mock data
    setTimeout(() => {
      setResults([
        {
          id: '1',
          address: '123 Oak Street, Los Angeles, CA 90001',
          parcelSize: 8500,
          buildableArea: 3200,
          zoning: 'R1',
          canFit: true,
          price: '$850,000'
        },
        {
          id: '2',
          address: '456 Maple Avenue, Los Angeles, CA 90002',
          parcelSize: 7200,
          buildableArea: 2800,
          zoning: 'R2',
          canFit: true,
          price: '$920,000'
        },
        {
          id: '3',
          address: '789 Pine Road, Los Angeles, CA 90003',
          parcelSize: 6800,
          buildableArea: 2100,
          zoning: 'R1',
          canFit: true,
          price: '$780,000'
        },
        {
          id: '4',
          address: '321 Elm Drive, Los Angeles, CA 90004',
          parcelSize: 9200,
          buildableArea: 3800,
          zoning: 'R2',
          canFit: true,
          price: '$1,150,000'
        }
      ]);
      setLoading(false);
    }, 1500);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">
              🏠 Backyard Builder Finder - Demo
            </h1>
            <span className="text-sm text-gray-500">Demo Mode</span>
          </div>
        </div>
      </header>

      <div className="flex h-[calc(100vh-73px)]">
        {/* Left Panel - Search Controls */}
        <div className="w-96 bg-white shadow-lg overflow-y-auto">
          <div className="p-6 space-y-6">
            {/* Search Area */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Search Area
              </label>
              <input
                type="text"
                value={searchArea}
                onChange={(e) => setSearchArea(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="City, ZIP, or address"
              />
            </div>

            {/* Unit Size */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Unit Size (sq ft)
              </label>
              <input
                type="number"
                value={unitSize}
                onChange={(e) => setUnitSize(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Filters */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Filters
              </label>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={excludePools}
                    onChange={(e) => setExcludePools(e.target.checked)}
                    className="mr-2"
                  />
                  <span className="text-sm">Exclude properties with pools</span>
                </label>
              </div>
            </div>

            {/* Search Button */}
            <button
              onClick={handleSearch}
              disabled={loading}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
            >
              {loading ? 'Searching...' : 'Search Properties'}
            </button>

            {/* Results */}
            {results.length > 0 && (
              <div className="border-t pt-4">
                <h3 className="text-lg font-semibold mb-3">
                  Results ({results.length} properties)
                </h3>
                <div className="space-y-3">
                  {results.map((result) => (
                    <div
                      key={result.id}
                      className="border rounded-lg p-3 hover:bg-gray-50 cursor-pointer transition-colors"
                    >
                      <div className="font-medium text-sm">{result.address}</div>
                      <div className="text-xs text-gray-600 mt-1">
                        <div>Parcel: {result.parcelSize.toLocaleString()} sq ft</div>
                        <div>Buildable: {result.buildableArea.toLocaleString()} sq ft</div>
                        <div>Zoning: {result.zoning}</div>
                        <div className="font-semibold text-green-600 mt-1">
                          ✓ Can fit {unitSize} sq ft unit
                        </div>
                        <div className="text-blue-600 font-semibold">{result.price}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Map */}
        <div className="flex-1 relative">
          <Map results={results} />
          
          {/* Map Legend */}
          <div className="absolute bottom-4 right-4 bg-white rounded-lg shadow-lg p-4">
            <h4 className="font-semibold text-sm mb-2">Legend</h4>
            <div className="space-y-1 text-xs">
              <div className="flex items-center">
                <div className="w-4 h-4 bg-blue-500 mr-2"></div>
                <span>Selected Parcel</span>
              </div>
              <div className="flex items-center">
                <div className="w-4 h-4 bg-green-500 mr-2"></div>
                <span>Buildable Area</span>
              </div>
              <div className="flex items-center">
                <div className="w-4 h-4 bg-gray-400 mr-2"></div>
                <span>Building Footprint</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}