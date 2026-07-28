import type { BusInfo } from '@/utils/parseBusInfo';
import { getLineColor } from '@/utils/lineColors';

export function hasIncident(raw: string): boolean {
  const match = raw.match(/incidencias?|desv[ií]os|corte|aver[ií]a/i);
  if (!match) return false;

  const sentenceStart = Math.max(
    raw.lastIndexOf('.', match.index),
    raw.lastIndexOf(',', match.index),
    raw.lastIndexOf(';', match.index)
  ) + 1;

  const clause = raw.slice(sentenceStart, match.index).toLowerCase();
  const negated = /\b(no|sin|ningun[ao]?)\b/.test(clause);

  return !negated;
}

interface BusCardProps {
  info: BusInfo;
  onFlyTo?: () => void;
}

export default function BusCard({ info, onFlyTo }: BusCardProps) {
  const hasIncidentFlag = hasIncident(info.raw);
  const lineColor = getLineColor(info.line || '');

  return (
    <div className="bus-row-card">
      <div className="bus-row-card__header">
        <span
          className="status-badge"
          style={{ background: lineColor.bg, color: lineColor.fg, fontWeight: 700 }}
        >
          {info.line || '5'}
        </span>
        <p className="bus-row-card__stop">{info.stopName || 'Parada 5907 (Sevilla)'}</p>

        {hasIncidentFlag && (
          <span
            className="status-badge"
            style={{ background: 'rgba(213, 94, 0, 0.12)', color: '#D55E00' }}
          >
            <span className="status-badge__symbol" aria-hidden="true">⚠️</span>
            Con desvíos
          </span>
        )}
      </div>

      <p className="bus-row-card__eta">
        <strong>{info.firstBusMinutes != null ? info.firstBusMinutes : '5'} min</strong>
        {info.secondBusMinutes != null && (
          <span className="bus-row-card__eta-secondary"> · Siguiente: {info.secondBusMinutes} min</span>
        )}
      </p>

      {onFlyTo && (
        <button type="button" onClick={onFlyTo} className="action-chip" style={{ marginTop: '0.5rem' }}>
          Ver ubicación en mapa 3D →
        </button>
      )}
    </div>
  );
}
