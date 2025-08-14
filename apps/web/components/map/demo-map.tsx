'use client';

import { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

interface DemoMapProps {
  results: any[];
}

export default function DemoMap({ results }: DemoMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!mapContainer.current) return;

    // Initialize map
    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '© OpenStreetMap Contributors'
          }
        },
        layers: [
          {
            id: 'osm',
            type: 'raster',
            source: 'osm'
          }
        ]
      },
      center: [-118.2437, 34.0522], // Los Angeles
      zoom: 11
    });

    // Add navigation controls
    map.current.addControl(new maplibregl.NavigationControl(), 'top-right');

    // Add sample parcels when results are available
    if (results.length > 0) {
      // Sample parcel locations around LA
      const sampleParcels = [
        { lng: -118.2587, lat: 34.0450 },
        { lng: -118.2337, lat: 34.0622 },
        { lng: -118.2687, lat: 34.0350 },
        { lng: -118.2237, lat: 34.0722 }
      ];

      results.forEach((result, index) => {
        if (sampleParcels[index]) {
          const marker = new maplibregl.Marker({ color: '#3B82F6' })
            .setLngLat([sampleParcels[index].lng, sampleParcels[index].lat])
            .setPopup(
              new maplibregl.Popup().setHTML(`
                <div class="p-2">
                  <div class="font-semibold">${result.address}</div>
                  <div class="text-sm mt-1">
                    <div>Buildable: ${result.buildableArea.toLocaleString()} sq ft</div>
                    <div class="text-green-600">✓ Unit fits</div>
                    <div class="text-blue-600 font-semibold">${result.price}</div>
                  </div>
                </div>
              `)
            )
            .addTo(map.current!);
        }
      });
    }

    return () => {
      map.current?.remove();
    };
  }, [results]);

  return <div ref={mapContainer} className="w-full h-full" />;
}