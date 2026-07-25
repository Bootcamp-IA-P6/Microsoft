import { stopCoordinates } from '@/utils/geoData';

const stopNames = Object.keys(stopCoordinates);

const COMMON_WORDS = new Set([
  'EL', 'LA', 'LOS', 'LAS', 'DE', 'DEL', 'EN', 'POR', 'CON', 'UN',
  'UNA', 'Y', 'E', 'O', 'A', 'AL', 'QUE', 'SE', 'NO', 'ES', 'SU',
  'LE', 'LO', 'PARA', 'DON', 'DOÑA', 'SAN', 'SANTA',
]);

function normalize(text: string): string {
  return text
    .toUpperCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim();
}

function isValidStopName(name: string): boolean {
  const normalized = normalize(name);
  if (normalized.length < 4) return false;
  if (COMMON_WORDS.has(normalized)) return false;
  return true;
}

export function extractFirstStop(...texts: string[]): string | null {
  for (const text of texts) {
    if (!text) continue;
    const upper = normalize(text);

    for (const stopName of stopNames) {
      if (!isValidStopName(stopName)) continue;
      if (upper.includes(normalize(stopName))) {
        return stopName;
      }
    }
  }
  return null;
}

export function extractAllStops(...texts: string[]): string[] {
  const found: string[] = [];
  const seen = new Set<string>();

  for (const text of texts) {
    if (!text) continue;
    const upper = normalize(text);

    for (const stopName of stopNames) {
      if (!isValidStopName(stopName)) continue;
      const key = normalize(stopName);
      if (!seen.has(key) && upper.includes(key)) {
        seen.add(key);
        found.push(stopName);
      }
    }
  }

  return found;
}