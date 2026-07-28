export const stopCoordinates: Record<string, [number, number]> = {
  LAVAPIES: [-3.7008, 40.4088],
  'PUERTA DEL SOL': [-3.7038, 40.4168],
  SOL: [-3.7038, 40.4168],
  'PLAZA CASTILLA': [-3.6892, 40.4669],
  'EMBAJADORES': [-3.7001, 40.4056],
  'ATOCHA': [-3.6905, 40.4066],
  'ATOCHA RENFE': [-3.6905, 40.4066],
  'CIBELES': [-3.6931, 40.4196],
  'NEPTUNO': [-3.6951, 40.4155],
  'GRAN VÍA': [-3.7022, 40.4207],
  'ALCALÁ': [-3.7022, 40.4207],
  'TIRSO DE MOLINA': [-3.7048, 40.4122],
  'ANTÓN MARTÍN': [-3.6995, 40.4101],
  'DELICIA': [-3.6920, 40.4060],
  'LEGAZPI': [-3.6958, 40.4016],
  'MENÉNDEZ PELAYO': [-3.6879, 40.4077],
  'PACÍFICO': [-3.6862, 40.4040],
  'CONDE DE CASAL': [-3.6810, 40.4080],
  'MANUEL BECERRA': [-3.6798, 40.4217],
  'VENTAS': [-3.6700, 40.4270],
  'GÓNGORA': [-3.6730, 40.4330],
  'ARTURO SORIA': [-3.6600, 40.4450],
  'AVENIDA DE AMÉRICA': [-3.6774, 40.4425],
  'NUEVOS MINISTERIOS': [-3.6931, 40.4474],
  'CUATRO CAMINOS': [-3.7042, 40.4480],
  'MONCLOA': [-3.7178, 40.4369],
  'ARGÜELLES': [-3.7148, 40.4328],
  'PRÍNCIPE PÍO': [-3.7200, 40.4210],
  'ÓPERA': [-3.7086, 40.4182],
  'CALLAO': [-3.7048, 40.4200],
  'TRIBUNAL': [-3.7020, 40.4263],
  'BILLBAO': [-3.7045, 40.4306],
  'IGLESIA': [-3.7020, 40.4357],
  'RÍOS ROSAS': [-3.7030, 40.4410],
  'SANTIAGO BERNABÉU': [-3.6916, 40.4524],
  'PADRE DAMIÁN': [-3.4199, 40.4656],
  'AVENIDA DE LA PAZ': [-3.6599, 40.4700],
  'BARRIO DEL PILAR': [-3.7100, 40.4800],
  'LA ELIPA': [-3.7300, 40.4900],
  'MIRASIERRA': [-3.7400, 40.5050],
  'HERMANOS GARCÍA NOBLEJAS': [-3.6500, 40.4100],
  'ALONSO MARTÍNEZ': [-3.6960, 40.4277],
  'COLÓN': [-3.6927, 40.4250],
  'SERRANO': [-3.6876, 40.4287],
  'VELÁZQUEZ': [-3.6864, 40.4323],
  'CASTELLANA': [-3.6900, 40.4450],
  'RUBÉN DARÍO': [-3.6901, 40.4322],
  'EMILIA': [-3.7170, 40.4065],
  'ACACIAS': [-3.7080, 40.4020],
  'PALOS DE LA FRONTERA': [-3.7000, 40.4030],
  'CIRCULAR': [-3.6950, 40.4010],
  'PLAZA ELÍPTICA': [-3.7180, 40.3850],
  'USERA': [-3.7180, 40.3850],
  'ALMENDRALES': [-3.7250, 40.3700],
  'VILLAVERDE': [-3.7450, 40.3500],
  'VALLEHERMOSO': [-3.6850, 40.4500],
  'LA PAZ': [-3.6880, 40.4590],
  'VAGUADA': [-3.6800, 40.4650],
  'RAMÓN Y CAJAL': [-3.6740, 40.4600],
  'CANILLAS': [-3.6400, 40.4350],
  'ESPERANZA': [-3.6550, 40.4400],
  'PUEBLO NUEVO': [-3.6480, 40.4380],
  'EL CARMEN': [-3.6380, 40.4370],
  'QUINTANA': [-3.6420, 40.4360],
  'ALONSO CANO': [-3.6480, 40.4300],
  'SUANCES': [-3.6550, 40.4280],
  'SAN BLAS': [-3.6250, 40.4330],
  'LAS ROSAS': [-3.6120, 40.4310],
  'ESTRELLA': [-3.6820, 40.4140],
  'PAVONES': [-3.6780, 40.4180],
  'SEVILLA': [-3.7000, 40.4180],
  'BANCO DE ESPAÑA': [-3.6990, 40.4175],
  'RETIRO': [-3.6850, 40.4150],
  'IBIZA': [-3.6810, 40.4190],
  'SAINZ DE BARANDA': [-3.6760, 40.4200],
  'O DONNELL': [-3.6740, 40.4230],
};

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