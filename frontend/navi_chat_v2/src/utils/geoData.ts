import { stopCoordsFromGold } from './stopsFromGold';

// Coordenadas reales de las 52 paradas in-scope (GTFS via Gold)
export const stopCoordinates: Record<string, [number, number]> = stopCoordsFromGold;

export function getStopCoords(stopName: string): [number, number] | null {
  const key = stopName.toUpperCase().trim();
  return stopCoordinates[key] ?? null;
}

const routeSegments: Record<string, [number, number][]> = {
  '5': [
    [-3.7038, 40.4168],
    [-3.7022, 40.4180],
    [-3.7000, 40.4180],
    [-3.6990, 40.4175],
    [-3.6985, 40.4165],
    [-3.6980, 40.4155],
    [-3.6975, 40.4145],
    [-3.6970, 40.4135],
    [-3.6965, 40.4125],
    [-3.6960, 40.4115],
    [-3.6958, 40.4100],
    [-3.6950, 40.4090],
    [-3.6945, 40.4080],
    [-3.6942, 40.4070],
    [-3.6940, 40.4060],
    [-3.6935, 40.4055],
  ],
  '27': [
    [-3.7008, 40.4088],
    [-3.7005, 40.4095],
    [-3.7002, 40.4105],
    [-3.7000, 40.4115],
    [-3.6998, 40.4125],
    [-3.6995, 40.4135],
    [-3.6992, 40.4145],
    [-3.6990, 40.4155],
    [-3.6988, 40.4165],
    [-3.6985, 40.4175],
    [-3.6982, 40.4185],
    [-3.6980, 40.4195],
    [-3.6978, 40.4205],
    [-3.6975, 40.4215],
  ],
  '146': [
    [-3.7022, 40.4207],
    [-3.7015, 40.4215],
    [-3.7008, 40.4225],
    [-3.7002, 40.4235],
    [-3.6995, 40.4245],
    [-3.6990, 40.4255],
    [-3.6985, 40.4265],
    [-3.6980, 40.4275],
    [-3.6975, 40.4285],
    [-3.6970, 40.4295],
    [-3.6965, 40.4305],
  ],
  '51': [
    [-3.7022, 40.4207],
    [-3.7010, 40.4215],
    [-3.7000, 40.4220],
    [-3.6990, 40.4225],
    [-3.6980, 40.4230],
    [-3.6970, 40.4230],
    [-3.6960, 40.4230],
    [-3.6950, 40.4230],
  ],
};

function _generateMadridRoute(stopCoords: [number, number]): [number, number][] {
  const CENTRO: [number, number] = [-3.7038, 40.4168];
  const SUR: [number, number] = [-3.6905, 40.4066];
  const NORTE: [number, number] = [-3.6931, 40.4474];
  const OESTE: [number, number] = [-3.7200, 40.4210];

  const dst = stopCoords[1] < 40.410
    ? CENTRO
    : stopCoords[1] > 40.440
      ? SUR
      : stopCoords[0] < -3.705
        ? CENTRO
        : stopCoords[0] > -3.680
          ? OESTE
          : NORTE;

  const dx = dst[0] - stopCoords[0];
  const dy = dst[1] - stopCoords[1];
  const len = Math.sqrt(dx * dx + dy * dy);

  const nx = -dy / len;
  const ny = dx / len;
  const amplitude = len * 0.08;

  const NUM = 8;
  const result: [number, number][] = [];
  for (let i = 0; i <= NUM; i++) {
    const t = i / NUM;
    const lx = stopCoords[0] + dx * t;
    const ly = stopCoords[1] + dy * t;
    const offset = amplitude * Math.sin(t * Math.PI);
    result.push([lx + nx * offset, ly + ny * offset]);
  }
  return result;
}

export function getRouteLineString(stopId?: string, stopCoords?: [number, number]): GeoJSON.Feature<GeoJSON.LineString> | null {
  if (stopId && routeSegments[stopId]) {
    return {
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: routeSegments[stopId] },
      properties: {},
    };
  }

  if (!stopCoords) return null;

  if (stopId && !stopCoords) {
    const resolved = getStopCoords(stopId);
    if (resolved) stopCoords = resolved;
  }

  const raw = _generateMadridRoute(stopCoords);
  return {
    type: 'Feature',
    geometry: { type: 'LineString', coordinates: raw },
    properties: {},
  };
}
