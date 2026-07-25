import { getStopNameById } from './stopNames';

export interface BusInfo {
  line: string;
  stopName: string;
  destination: string;
  firstBusMinutes: number;
  secondBusMinutes: number | null;
  raw: string;
}

const LINE_RE = /líneas?\s*(\d+)/i;
const STOP_ID_RE = /parada\s+(\d{3,5})/i;
const STOP_NAME_RE = /(?:parada|estación)\s+(?:de\s+)?([A-ZÁÉÍÓÚÑ][a-záéíóúñ]*(?:\s*[-–—]\s*[A-ZÁÉÍÓÚÑ][a-záéíóúñ]*)*)/i;
const FIRST_BUS_RE = /(?:en|tarda)\s*(\d+)\s*(?:minutos?|min)/i;
const SECOND_BUS_RE = /(?:siguiente|segundo)(?: bus| autobús)? (?:pasará|llegará|en)? (?:en )?(\d+) min/i;
const DESTINATION_RE = /con\s+destino\s+([A-ZÁÉÍÓÚÑa-záéíóúñ][A-ZÁÉÍÓÚÑa-záéíóúñ\s-]+)/i;

const NEGATIVE_PHRASES = [
  'no tengo suficiente información',
  'no se espera la llegada de un bus',
  'no hay ningún autobús próximo',
  'especificar el nombre de la parada',
];

export function parseBusInfo(text: string): BusInfo | null {
  const lower = text.toLowerCase();
  for (const phrase of NEGATIVE_PHRASES) {
    if (lower.includes(phrase)) return null;
  }

  const lineMatch = text.match(LINE_RE);
  if (!lineMatch) return null;

  const line = lineMatch[1].replace(/\s+/g, '');

  const secondMatch = text.match(SECOND_BUS_RE);
  const secondBusMinutes = secondMatch ? Number(secondMatch[1]) : null;

  let firstText = text;
  if (secondMatch) {
    firstText = text.replace(secondMatch[0], '');
  }
  const firstMatch = firstText.match(FIRST_BUS_RE);
  const firstBusMinutes = firstMatch ? parseInt(firstMatch[1], 10) : 0;

  const stopIdMatch = text.match(STOP_ID_RE);
  const stopId = stopIdMatch ? stopIdMatch[1] : null;

  let stopName = '';
  if (stopId) {
    const mappedName = getStopNameById(stopId);
    stopName = mappedName ? `Parada ${stopId} (${mappedName})` : `Parada ${stopId}`;
  }
  if (!stopName) {
    const stopNameMatch = text.match(STOP_NAME_RE);
    if (stopNameMatch) {
      stopName = `Parada (${stopNameMatch[1].trim()})`;
    }
  }

  const destMatch = text.match(DESTINATION_RE);
  const destination = destMatch ? destMatch[1].trim() : '';

  return { line, stopName, destination, firstBusMinutes, secondBusMinutes, raw: text };
}

export function isBusRelated(text: string): boolean {
  return (
    /(?:autobús|bus|línea|líneas|parada|estación|llegad|tard[a-z]*|minuto)/i.test(text)
  );
}
