import type { BusInfo } from '@/utils/parseBusInfo';

interface BusCardProps {
  info: BusInfo;
  onFlyTo?: () => void;
}

export default function BusCard({ info, onFlyTo }: BusCardProps) {
  const hasIncident = /incidencias?|desv[ií]os|corte|aver[ií]a/i.test(info.raw);

  return (
    <div className="bus-row-card">
      <div className="bus-row-card__header">
        <span
          className="status-badge"
          style={{ background: 'var(--color-accent)', color: 'var(--color-accent-on)', fontWeight: 700 }}
        >
          {info.line || '5'}
        </span>
        <p className="bus-row-card__stop">{info.stopName || 'Parada 5907 (Sevilla)'}</p>

        {hasIncident && (
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
