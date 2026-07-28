// src/utils/stopNames.ts
import { goldStops } from './stopsFromGold';

export const stopIdToName: Record<string, string> = {};
export const stopNameToId: Record<string, string> = {};

for (const s of goldStops) {
  stopIdToName[s.stop_id] = s.stop_name;
  // Para nombre → id, guardamos solo la primera ocurrencia (evita sobreescribir)
  const key = s.stop_name.toUpperCase();
  if (!stopNameToId[key]) {
    stopNameToId[key] = s.stop_id;
  }
}

export function getStopNameById(id: string): string | undefined {
  return stopIdToName[id];
}

export function getStopIdByName(name: string): string | undefined {
  return stopNameToId[name.toUpperCase().trim()];
}
