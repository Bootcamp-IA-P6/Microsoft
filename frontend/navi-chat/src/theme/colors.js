// theme/colors.js
// Paleta Okabe-Ito: la misma que ya usan en el Streamlit de Navi.
// Elegida porque es distinguible bajo las formas más comunes de daltonismo
// (protanopia, deuteranopia, tritanopia) sin perder contraste en pantalla.
//
// REGLA DE ACCESIBILIDAD (no negociable): el color NUNCA es el único portador
// de significado. Cada estado también lleva un ícono/símbolo Y texto.
// Ver components/StatusIcon.jsx para el mapeo símbolo <-> estado.

export const okabeIto = {
  black: '#000000',
  orange: '#E69F00',
  skyBlue: '#56B4E9',
  bluishGreen: '#009E73',
  yellow: '#F0E442',
  blue: '#0072B2',
  vermillion: '#D55E00',
  purple: '#CC79A7',
};

// Mapeo semántico: estado de negocio -> color + rol de contraste.
// `on` = color de texto/ícono que va SOBRE ese fondo para mantener AA (4.5:1).
export const semanticColor = {
  busLlegando: { bg: okabeIto.bluishGreen, on: '#FFFFFF' },
  sinBusProximo: { bg: '#E5E5E5', on: okabeIto.black },
  incidenciaActiva: { bg: okabeIto.vermillion, on: '#FFFFFF' },
  datoObsoleto: { bg: okabeIto.yellow, on: okabeIto.black }, // amarillo: SIEMPRE con texto oscuro encima, nunca blanco
  avisoCabecera: { bg: okabeIto.blue, on: '#FFFFFF' },
  neutro: { bg: okabeIto.skyBlue, on: okabeIto.black },
};

// Tokens de foco de teclado — visibles en cualquier fondo de la paleta.
export const focusRing = {
  color: okabeIto.black,
  width: '3px',
  offset: '2px',
};
