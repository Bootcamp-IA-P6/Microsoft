import { useEffect, useRef } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { Lang } from '@/i18n/translations';

interface FlyTarget {
  lng: number;
  lat: number;
  zoom: number;
}

interface MapPlaceholderProps {
  className?: string;
  language: Lang;
  flyTarget?: FlyTarget | null;
}

const MAP_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    'carto-light': {
      type: 'raster',
      tiles: [
        'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
        'https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
      ],
      tileSize: 256,
      attribution: '&copy; OpenStreetMap &copy; CARTO',
    },
  },
  layers: [
    {
      id: 'carto-light-layer',
      type: 'raster',
      source: 'carto-light',
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

function createMarkerEl(): HTMLElement {
  const el = document.createElement('div');
  el.style.width = '20px';
  el.style.height = '20px';
  el.style.backgroundColor = '#00E5FF';
  el.style.borderRadius = '50%';
  el.style.border = '3px solid #FFFFFF';
  el.style.boxShadow = '0 0 10px rgba(0,0,0,0.5)';
  el.style.filter = 'none';
  return el;
}

export default function MapPlaceholder({ className = '', flyTarget }: MapPlaceholderProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);

  useEffect(() => {
    if (mapRef.current || !mapContainer.current) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: MAP_STYLE,
      center: [-3.7038, 40.4168],
      zoom: 12,
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!mapContainer.current) return;

    const observer = new ResizeObserver(() => {
      mapRef.current?.resize();
    });

    observer.observe(mapContainer.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!flyTarget || !mapRef.current) return;
    mapRef.current.flyTo({
      center: [flyTarget.lng, flyTarget.lat],
      zoom: flyTarget.zoom,
      duration: 1200,
    });
  }, [flyTarget]);

  useEffect(() => {
    if (!wrapperRef.current) return;

    const updateFilter = () => {
      if (!wrapperRef.current) return;
      const isHighContrast = document.documentElement.classList.contains('high-contrast');
      wrapperRef.current.style.filter = isHighContrast
        ? 'invert(90%) hue-rotate(180deg)'
        : '';
    };

    updateFilter();

    const observer = new MutationObserver(updateFilter);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const handler = (e: Event) => {
      const { lng, lat, zoom = 16 } = (e as CustomEvent).detail;
      const map = mapRef.current;
      if (!map) return;

      map.flyTo({ center: [lng, lat], zoom, essential: true, duration: 1200 });

      markerRef.current?.remove();
      const marker = new maplibregl.Marker({ element: createMarkerEl() })
        .setLngLat([lng, lat])
        .addTo(map);
      markerRef.current = marker;
    };

    window.addEventListener('map:flyTo', handler);
    return () => window.removeEventListener('map:flyTo', handler);
  }, []);

  return (
    <div ref={wrapperRef} className={`relative ${className}`}>
      <div ref={mapContainer} className="h-full w-full" />
    </div>
  );
}