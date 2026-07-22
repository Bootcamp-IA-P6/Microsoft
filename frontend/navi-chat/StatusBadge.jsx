import StatusBadge from './StatusBadge';

function minutesFromSeconds(seconds) {
  if (seconds == null) return null;
  return Math.round(seconds / 60);
}

// BusRowCard: renderiza UNA fila con la forma de gold_emt_stop_line.
// Sigue el "Tratamiento de NULL" del contrato §8 al pie de la letra:
//   - sin bus -> eta_* NULL, has_upcoming_bus=false
//   - alert_active=false -> textos alert NULL
//   - freq NULL -> "no tengo ese dato todavía" (nunca inventar)
export default function BusRowCard({ row }) {
  const min1 = minutesFromSeconds(row.eta_seconds_1);
  const min2 = minutesFromSeconds(row.eta_seconds_2);

  return (
    <article className="bus-row-card" aria-label={`Línea ${row.line_label}, ${row.stop_name}`}>
      <header className="bus-row-card__header">
        <span className="bus-row-card__line" aria-hidden="true">
          {row.line_label}
        </span>
        <div>
          <p className="bus-row-card__stop">{row.stop_name}</p>
          {row.direction_text && (
            <p className="bus-row-card__direction">{row.direction_text}</p>
          )}
        </div>
      </header>

      <div className="bus-row-card__badges">
        {row.is_stale && <StatusBadge kind="datoObsoleto" />}
        {row.alert_active && <StatusBadge kind="incidenciaActiva" />}
        {row.origin_stop_notice && <StatusBadge kind="avisoCabecera" />}
      </div>

      {row.has_upcoming_bus ? (
        <p className="bus-row-card__eta">
          <StatusBadge kind="busLlegando">
            Próximo bus en {min1} min
          </StatusBadge>
          {min2 != null && (
            <span className="bus-row-card__eta-secondary">
              {' '}
              · siguiente en {min2} min
            </span>
          )}
        </p>
      ) : (
        <p className="bus-row-card__eta">
          <StatusBadge kind="sinBusProximo" />
        </p>
      )}

      {row.alert_active && (
        <p className="bus-row-card__alert">
          {row.alert_header}
          {row.alert_url && (
            <>
              {' '}
              <a href={row.alert_url} target="_blank" rel="noreferrer">
                Más información
              </a>
            </>
          )}
        </p>
      )}

      <p className="bus-row-card__freq">
        Frecuencia laborable:{' '}
        {row.freq_observed_weekday_min != null
          ? `cada ${row.freq_observed_weekday_min} min`
          : 'todavía no tengo ese dato'}
      </p>
    </article>
  );
}
