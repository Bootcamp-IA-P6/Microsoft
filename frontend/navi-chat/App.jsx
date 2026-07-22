import { semanticColor } from '../theme/colors';

// StatusBadge: color + símbolo + texto, siempre los tres juntos.
// Así el significado no depende de distinguir el color (regla de accesibilidad
// del proyecto: ver theme/colors.js).
//
// `kind` acepta: 'busLlegando' | 'sinBusProximo' | 'incidenciaActiva' | 'datoObsoleto' | 'avisoCabecera'

const CONFIG = {
  busLlegando: { symbol: '●', label: 'Bus en camino' },
  sinBusProximo: { symbol: '—', label: 'Sin bus próximo' },
  incidenciaActiva: { symbol: '⚠', label: 'Incidencia activa' },
  datoObsoleto: { symbol: '↻', label: 'Dato desactualizado' },
  avisoCabecera: { symbol: 'ⓘ', label: 'Parada de cabecera' },
};

export default function StatusBadge({ kind, children }) {
  const { bg, on } = semanticColor[kind];
  const { symbol, label } = CONFIG[kind];

  return (
    <span
      className="status-badge"
      style={{ backgroundColor: bg, color: on }}
      role="status"
    >
      <span aria-hidden="true" className="status-badge__symbol">
        {symbol}
      </span>
      <span>{children || label}</span>
    </span>
  );
}
