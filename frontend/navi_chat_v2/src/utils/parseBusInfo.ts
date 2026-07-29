import { getStopNameById } from './stopNames';

export interface BusInfo {
  line: string;
  stopName: string;
  destination: string;
  firstBusMinutes: number;
  secondBusMinutes: number | null;
  raw: string;
}

const LINE_RE = /líneas?\s*([A-Za-z]?\d+[A-Za-z]?)/i;
const STOP_ID_RE = /parada\s+(\d{3,5})/i;
const STOP_NAME_RE = /(?:parada|estación)\s+(?:de\s+)?([A-ZÁÉÍÓÚÑ][a-záéíóúñ]*(?:\s*[-–—]\s*[A-ZÁÉÍÓÚÑ][a-záéíóúñ]*)*)/i;
// Captura tiempos en formatos: "en 7 min", "tarda 7 min", ": 7 min", "7 minutos"
const FIRST_BUS_RE = /(?:en|tarda|:\s*)(\d+)\s*(?:minutos?|min)/i;
// "siguiente bus en 21 min", "siguiente: 21 min", "(siguiente bus en 21 min)"
const SECOND_BUS_RE = /(?:siguiente|segundo)(?: bus| autobús)?[\s:]*(?:pasará |llegará |en )?(\d+)\s*min/i;
const DESTINATION_RE = /(?:con\s+destino|hacia|→)\s+([A-ZÁÉÍÓÚÑa-záéíóúñ][A-ZÁÉÍÓÚÑa-záéíóúñ\s-]+)/i;

const NEGATIVE_PHRASES = [
  'no tengo suficiente información',
  'no se espera la llegada de un bus',
  'no hay ningún autobús próximo',
  'especificar el nombre de la parada',
  'no puedo obtener',
  'no he podido obtener',
  'no he podido acceder',
  'problema técnico',
  'error técnico',
  'intenta de nuevo más tarde',
  'intenta consultarlo de nuevo',
  'no puedo acceder a los datos',
  'no puedo acceder a la información',
];

export function parseBusInfo(text: string): BusInfo | null {
  const lower = text.toLowerCase();
  for (const phrase of NEGATIVE_PHRASES) {
    if (lower.includes(phrase)) return null;
  }

  const lineMatch = text.match(LINE_RE);
  if (!lineMatch) return null;

  const line = lineMatch[1].replace(/\s+/g, '');

  // Extract second bus time first, then remove it from text to avoid confusing first bus regex
  const secondMatch = text.match(SECOND_BUS_RE);
  const secondBusMinutes = secondMatch ? Number(secondMatch[1]) : null;

  let firstText = text;
  if (secondMatch) {
    firstText = text.replace(secondMatch[0], '');
  }
  const firstMatch = firstText.match(FIRST_BUS_RE);
  const firstBusMinutes = firstMatch ? parseInt(firstMatch[1], 10) : 0;

  // Extract stop ID — but avoid matching the line number itself
  const stopIdMatch = text.match(STOP_ID_RE);
  const stopId = stopIdMatch ? stopIdMatch[1] : null;

  let stopName = '';
  if (stopId) {
    const mappedName = getStopNameById(stopId);
    stopName = mappedName ? `${mappedName}` : `Parada ${stopId}`;
  }
  if (!stopName) {
    const stopNameMatch = text.match(STOP_NAME_RE);
    if (stopNameMatch) {
      stopName = stopNameMatch[1].trim();
    }
  }

  // Extract destination (hacia X, → X, con destino X)
  const destMatch = text.match(DESTINATION_RE);
  const destination = destMatch ? destMatch[1].trim() : '';

  return { line, stopName, destination, firstBusMinutes, secondBusMinutes, raw: text };
}

export function isBusRelated(text: string): boolean {
  return (
    /(?:autobús|bus|línea|líneas|parada|estación|llegad|tard[a-z]*|minuto)/i.test(text)
  );
}
