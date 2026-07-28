import { useEffect, useRef } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { Lang } from '@/i18n/translations';
import MapLibreInlineWorker from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&inline';
import { getStopIdByName } from '@/utils/stopNames';
import { stopCoordinates } from '@/utils/geoData';

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

function createMarkerEl(isHighlighted = false): HTMLElement {
  const el = document.createElement('div');
  el.style.width = isHighlighted ? '20px' : '14px';
  el.style.height = isHighlighted ? '20px' : '14px';
  el.style.backgroundColor = '#00E5FF';
  el.style.borderRadius = '50%';
  el.style.border = isHighlighted ? '3px solid #FFFFFF' : '2px solid #FFFFFF';
  el.style.boxShadow = isHighlighted
    ? '0 0 10px rgba(0,0,0,0.5)'
    : '0 0 6px rgba(0,0,0,0.35)';
  el.style.filter = 'none';
  el.style.transform = 'translateY(-50%)';
  el.style.cursor = 'pointer';
  el.style.zIndex = isHighlighted ? '10' : '5';
  el.style.transition = 'width 0.15s, height 0.15s, box-shadow 0.15s';
  return el;
}

function createStopPopupContent(stopName: string, _stopCoordinates: [number, number]): HTMLElement {
  const stopId = getStopIdByName(stopName);
  const displayName = stopId ? `${stopName} (${stopId})` : stopName;

  const container = document.createElement('div');
  container.className = 'map-popup';

  const nameEl = document.createElement('strong');
  nameEl.className = 'map-popup__name';
  nameEl.textContent = displayName;
  container.appendChild(nameEl);

  const btn = document.createElement('button');
  btn.className = 'map-popup__btn';
  btn.textContent = 'Ver horarios';
  btn.addEventListener('click', () => {
    const question = `¿Qué buses llegan ahora a ${stopName}?`;
    window.dispatchEvent(new CustomEvent('chat:ask', { detail: { question } }));
    window.dispatchEvent(new CustomEvent('nav:changeView', { detail: { view: 'split' } }));
  });
  container.appendChild(btn);

  return container;
}

export default function Map({ className = '', flyTarget, isMapVisible }: MapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const stopMarkersRef = useRef<maplibregl.Marker[]>([]);

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
              'coalesce',
              ['get', 'height'],
              ['get', 'render_height'],
              ['get', 'elevation'],
              25,
            ],
            'fill-extrusion-base': [
              'coalesce',
              ['get', 'min_height'],
              0,
            ],
            'fill-extrusion-opacity': 0.85,
            'fill-extrusion-vertical-gradient': true,
          },
        });
      }

      // Precargar marcadores de todas las paradas conocidas
      addStopMarkers(map);
    });

    return () => {
      stopMarkersRef.current.forEach((m) => m.remove());
      stopMarkersRef.current = [];
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
      const { lng, lat, zoom = 16.5, stopName } = (e as CustomEvent).detail;
      const map = mapRef.current;
      if (!map) return;

      map.flyTo({ center: [lng, lat], zoom, pitch: 60, bearing: -20, essential: true, duration: 1200 });

      markerRef.current?.remove();
      const marker = new maplibregl.Marker({ element: createMarkerEl(true) })
        .setLngLat([lng, lat])
        .addTo(map);
      markerRef.current = marker;

      const coords: [number, number] = [lng, lat];
      const displayName = stopName
        ? stopName.charAt(0).toUpperCase() + stopName.slice(1).toLowerCase()
        : 'Parada';

      // Abrir popup inmediatamente
      popupRef.current?.remove();
      const popup = new maplibregl.Popup({ offset: 25, closeButton: true })
        .setLngLat(coords)
        .setDOMContent(createStopPopupContent(displayName, coords))
        .addTo(map);
      popupRef.current = popup;

      attachPopupToMarker(marker, coords, displayName);
    };

    window.addEventListener('map:flyTo', handler);
    return () => window.removeEventListener('map:flyTo', handler);
  }, []);

  function addStopMarkers(map: maplibregl.Map) {
    // Limpiar marcadores previos si los hay
    stopMarkersRef.current.forEach((m) => m.remove());
    stopMarkersRef.current = [];

    for (const [name, coords] of Object.entries(stopCoordinates)) {
      const el = createMarkerEl(false);
      el.title = name.charAt(0) + name.slice(1).toLowerCase();

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat(coords)
        .addTo(map);

      const displayName = name.charAt(0) + name.slice(1).toLowerCase();

      el.addEventListener('click', (e) => {
        e.stopPropagation();
        popupRef.current?.remove();

        const popup = new maplibregl.Popup({ offset: 25, closeButton: true })
          .setLngLat(coords)
          .setDOMContent(createStopPopupContent(displayName, coords))
          .addTo(map);
        popupRef.current = popup;

        map.flyTo({
          center: coords,
          zoom: Math.max(map.getZoom(), 16),
          duration: 600,
        });
      });

      stopMarkersRef.current.push(marker);
    }
  }

  function attachPopupToMarker(marker: maplibregl.Marker, stopCoords: [number, number], stopName: string) {
    const el = marker.getElement();
    // Clonar el elemento para eliminar listeners previos (evita acumulación)
    const newEl = el.cloneNode(true) as HTMLElement;
    el.parentNode?.replaceChild(newEl, el);

    newEl.addEventListener('click', (e) => {
      e.stopPropagation();
      popupRef.current?.remove();
      const map = mapRef.current;
      if (!map) return;

      const popup = new maplibregl.Popup({ offset: 25, closeButton: true })
        .setLngLat(stopCoords)
        .setDOMContent(createStopPopupContent(stopName, stopCoords))
        .addTo(map);
      popupRef.current = popup;
    });
  }

  useEffect(() => {
    const handler = (e: Event) => {
      const map = mapRef.current;
      if (!map) return;

      const { stopCoordinates: stopCoords, stopName } = (e as CustomEvent).detail;
      if (!stopCoords) return;

      markerRef.current?.remove();
      const marker = new maplibregl.Marker({ element: createMarkerEl(true) })
        .setLngLat(stopCoords)
        .addTo(map);
      markerRef.current = marker;

      popupRef.current?.remove();
      const popup = new maplibregl.Popup({ offset: 25, closeButton: true })
        .setLngLat(stopCoords)
        .setDOMContent(createStopPopupContent(stopName || 'Parada', stopCoords))
        .addTo(map);
      popupRef.current = popup;

      attachPopupToMarker(marker, stopCoords, stopName || 'Parada');

      map.flyTo({
        center: stopCoords,
        zoom: 16.5,
        pitch: 50,
        bearing: -10,
        duration: 2000,
      });
    };

    window.addEventListener('map:showRoute', handler);
    return () => window.removeEventListener('map:showRoute', handler);
  }, []);

  return (
    <div ref={wrapperRef} className={`relative map-wrapper ${className}`}>
      <div ref={mapContainer} className="h-full w-full" />
    </div>
  );
}
