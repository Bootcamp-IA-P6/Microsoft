import { getStopNameById } from './stopNames';

const STOP_ID_RE = /parada\s+(\d{3,5})/i;

export function enrichStopQuery(question: string): string {
  const match = question.match(STOP_ID_RE);
  if (!match) return question;
  const stopId = match[1];
  const stopName = getStopNameById(stopId);
  if (!stopName) return question;
  const nameInParens = new RegExp(`\\(${stopName}\\)`, 'i');
  if (nameInParens.test(question)) return question;
  return question.replace(match[0], `${match[0]} (${stopName})`);
}
