import { semanticColor } from '../theme/colors';
import { useTranslation } from '../context/LanguageContext';

// StatusBadge: color + símbolo + texto, siempre los tres juntos — el
// significado no depende de distinguir el color (ver theme/colors.js).
// `kind` acepta: 'busLlegando' | 'sinBusProximo' | 'incidenciaActiva' | 'datoObsoleto' | 'avisoCabecera'

const SYMBOLS = {
  busLlegando: '●',
  sinBusProximo: '—',
  incidenciaActiva: '⚠',
  datoObsoleto: '↻',
  avisoCabecera: 'ⓘ',
};

const LABEL_KEYS = {
  busLlegando: 'statusBusComing',
  sinBusProximo: 'statusNoBus',
  incidenciaActiva: 'statusAlert',
  datoObsoleto: 'statusStale',
  avisoCabecera: 'statusTerminus',
};

export default function StatusBadge({ kind, children }) {
  const { t } = useTranslation();
  const { bg, on } = semanticColor[kind];

  return (
    <span className="status-badge" style={{ backgroundColor: bg, color: on }} role="status">
      <span aria-hidden="true" className="status-badge__symbol">
        {SYMBOLS[kind]}
      </span>
      <span>{children || t(LABEL_KEYS[kind])}</span>
    </span>
  );
}
