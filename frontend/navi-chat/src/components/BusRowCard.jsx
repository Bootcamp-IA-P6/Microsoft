import StatusBadge from './StatusBadge';
import { useTranslation } from '../context/LanguageContext';

function minutesFromSeconds(seconds) {
  if (seconds == null) return null;
  return Math.round(seconds / 60);
}

// BusRowCard: renderiza UNA fila con la forma de gold_emt_stop_line.
// Sigue el "Tratamiento de NULL" del contrato §8: sin bus -> eta_* NULL;
// alert_active=false -> textos alert NULL; freq NULL -> "no tengo ese dato".
export default function BusRowCard({ row }) {
  const { t } = useTranslation();
  const min1 = minutesFromSeconds(row.eta_seconds_1);
  const min2 = minutesFromSeconds(row.eta_seconds_2);

  return (
    <article className="bus-row-card" aria-label={`${row.line_label}, ${row.stop_name}`}>
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
          <StatusBadge kind="busLlegando">{t('nextBusIn', min1)}</StatusBadge>
          {min2 != null && (
            <span className="bus-row-card__eta-secondary"> · {t('nextAfter', min2)}</span>
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
                {t('moreInfo')}
              </a>
            </>
          )}
        </p>
      )}

      <p className="bus-row-card__freq">
        {t('freqWeekday')}:{' '}
        {row.freq_observed_weekday_min != null
          ? t('freqEvery', row.freq_observed_weekday_min)
          : t('freqUnknown')}
      </p>
    </article>
  );
}
