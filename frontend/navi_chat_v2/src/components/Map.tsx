import { useEffect, useRef } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { Lang } from '@/i18n/translations';
import MapLibreInlineWorker from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&inline';

const __OriginalWorker = globalThis.Worker;
const __PatchedWorker = function (this: Worker, url: string | URL, options?: WorkerOptions): Worker {
  if (String(url) === '__maplibre_inline_worker__') {
    return new MapLibreInlineWorker(options);
  }
  return new __OriginalWorker(url, options);
} as unknown as typeof Worker;
__PatchedWorker.prototype = __OriginalWorker.prototype;
globalThis.Worker = __PatchedWorker;
maplibregl.setWorkerUrl('__maplibre_inline_worker__');

interface FlyTarget {
  lng: number;
  lat: number;
  zoom: number;
}

interface MapProps {
  className?: string;
  language: Lang;
  flyTarget?: FlyTarget | null;
  isMapVisible?: boolean;
}

function createMarkerEl(): HTMLElement {
  const el = document.createElement('div');
  el.style.width = '20px';
  el.style.height = '20px';
  el.style.backgroundColor = '#00E5FF';
  el.style.borderRadius = '50%';
  el.style.border = '3px solid #FFFFFF';
  el.style.boxShadow = '0 0 10px rgba(0,0,0,0.5)';
  el.style.filter = 'none';
  el.style.transform = 'translateY(-50%)';
  el.style.pointerEvents = 'none';
  return el;
}

export default function Map({ className = '', flyTarget, isMapVisible }: MapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);

  useEffect(() => {
    if (mapRef.current || !mapContainer.current) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://tiles.openfreemap.org/styles/bright',
      center: [-3.6983, 40.4172],
      zoom: 16.5,
      pitch: 60,
      bearing: -20,
      trackResize: true,
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    mapRef.current = map;

    map.on('error', (e) => {
      console.error('MapLibre Tile Error:', e.error);
    });

    map.on('load', () => {
      map.resize();

      map.setLight({
        anchor: 'viewport',
        color: '#ffffff',
        intensity: 0.5,
        position: [1.5, 180, 30],
      });

      if (!map.getLayer('3d-buildings')) {
        map.addLayer({
          id: '3d-buildings',
          source: 'openmaptiles',
          'source-layer': 'building',
          type: 'fill-extrusion',
          minzoom: 13,
          paint: {
            'fill-extrusion-color': [
              'interpolate',
              ['linear'],
              ['get', 'render_height'],
              0, '#e2e8f0',
              20, '#cbd5e1',
              50, '#94a3b8',
            ],
            'fill-extrusion-height': [
              'interpolate',
              ['linear'],
              ['zoom'],
              13, 0,
              14.5, ['coalesce', ['get', 'render_height'], ['get', 'height'], 15],
            ],
            'fill-extrusion-base': [
              'interpolate',
              ['linear'],
              ['zoom'],
              13, 0,
              14.5, ['coalesce', ['get', 'render_min_height'], ['get', 'min_height'], 0],
            ],
            'fill-extrusion-opacity': 0.85,
            'fill-extrusion-vertical-gradient': true,
          },
        });
      }
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!mapContainer.current) return;

    const resizeObserver = new ResizeObserver(() => {
      if (mapRef.current) {
        mapRef.current.resize();
      }
    });

    resizeObserver.observe(mapContainer.current);

    return () => resizeObserver.disconnect();
  }, []);

  useEffect(() => {
    if (!isMapVisible || !mapRef.current) return;
    setTimeout(() => mapRef.current?.resize(), 100);
    setTimeout(() => mapRef.current?.resize(), 500);
  }, [isMapVisible]);

  useEffect(() => {
    if (!flyTarget || !mapRef.current) return;
    mapRef.current.flyTo({
      center: [flyTarget.lng, flyTarget.lat],
      zoom: flyTarget.zoom ?? 16.5,
      pitch: 60,
      bearing: -20,
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
      const { lng, lat, zoom = 16.5 } = (e as CustomEvent).detail;
      const map = mapRef.current;
      if (!map) return;

      map.flyTo({ center: [lng, lat], zoom, pitch: 60, bearing: -20, essential: true, duration: 1200 });

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
