import { getStopNameById, getStopIdByName } from './stopNames';
import { stopCoordinates } from './geoData';

const STOP_ID_RE = /parada\s+(\d{3,5})/i;

function normalize(text: string): string {
  return text
    .toUpperCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim();
}

function findStopNameInQuestion(question: string): string | null {
  const normalizedQ = normalize(question);
  const stopNames = Object.keys(stopCoordinates);
  for (const name of stopNames) {
    const normalizedName = normalize(name);
    if (normalizedName.length >= 4 && normalizedQ.includes(normalizedName)) {
      return name;
    }
  }
  return null;
}

export function enrichStopQuery(question: string): string {
  // 1. ID → nombre: si el usuario escribe "parada 5907", añadir "(Sevilla)"
  const idMatch = question.match(STOP_ID_RE);
  if (idMatch) {
    const stopId = idMatch[1];
    const stopName = getStopNameById(stopId);
    if (stopName) {
      const nameInParens = new RegExp(`\\(${stopName}\\)`, 'i');
      if (!nameInParens.test(question)) {
        return question.replace(idMatch[0], `${idMatch[0]} (${stopName})`);
      }
    }
    return question;
  }

  // 2. Nombre → ID: si el usuario escribe "Gran Vía" sin ID, añadir "(parada 161)"
  const foundName = findStopNameInQuestion(question);
  if (foundName) {
    const stopId = getStopIdByName(foundName);
    if (stopId) {
      const idInParens = new RegExp(`\\(parada\\s+${stopId}\\)`, 'i');
      if (!idInParens.test(question)) {
        return `${question} (parada ${stopId})`;
      }
    }
  }

  return question;
}
