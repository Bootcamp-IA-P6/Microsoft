// i18n/translations.js
//
// Diccionario plano por clave. Nada de librerías externas (react-i18next, etc.)
// — para el tamaño de esta app, un objeto + un hook simple alcanza y evita
// una dependencia más que mantener antes de la demo.
//
// Para agregar un string nuevo: agréguelo en las 3 columnas (es/en/pt) con
// la MISMA clave. Si falta una traducción, useTranslation() cae de vuelta
// al español antes que mostrar la clave cruda en pantalla.

export const translations = {
  es: {
    tagline: 'Asistente inteligente de movilidad',
    welcomeMessage: 'Hola, soy Navi! Pregúntame por cualquier línea o parada cerca de Puerta del Sol.',
    inputPlaceholder: 'Ej: ¿cuánto tarda la línea 27?',
    inputLabel: 'Escribe tu pregunta sobre buses',
    askButton: 'Preguntar',
    loadingMessage: 'Navi está consultando…',
    errorMessage: 'No pude consultar los datos en este momento. Intenta de nuevo en unos segundos.',
    footerNote: 'Información en tiempo real de EMT Madrid',
    skipLink: 'Saltar al contenido principal',

    voiceAsk: 'Preguntar por voz',
    voiceStop: 'Detener grabación de voz',
    voiceErrorPermission: 'Necesito permiso para usar el micrófono.',
    voiceErrorNoSpeech: 'No escuché nada, intenta de nuevo.',
    voiceErrorGeneric: 'No pude escucharte, intenta de nuevo.',

    settingsTrigger: 'Preferencias',
    settingsAppearance: 'Apariencia',
    themeLight: 'Claro',
    themeDark: 'Oscuro',
    themeHighContrast: 'Alto contraste',
    settingsFontSize: 'Tamaño de letra',
    fontSizeNormal: 'Normal',
    fontSizeLarge: 'Grande',
    fontSizeXLarge: 'Muy grande',
    settingsLanguage: 'Idioma',

    statusBusComing: 'Bus en camino',
    statusNoBus: 'Sin bus próximo',
    statusAlert: 'Incidencia activa',
    statusStale: 'Dato desactualizado',
    statusTerminus: 'Parada de cabecera',
    nextBusIn: (min) => `Próximo bus en ${min} min`,
    nextAfter: (min) => `siguiente en ${min} min`,
    moreInfo: 'Más información',
    freqWeekday: 'Frecuencia laborable',
    freqEvery: (min) => `cada ${min} min`,
    freqUnknown: 'todavía no tengo ese dato',

    heroTitle: '¡Hola! Soy Navi 👋',
    heroSubtitle: '¿Cómo puedo ayudarte a moverte hoy?',
    quickActionNextBus: '🚌 Próximos buses',
    quickActionPromptNextBus: '¿Qué buses llegan ahora a mi parada?',
    quickActionHowReach: '📍 ¿Cómo llego a Gran Vía?',
    quickActionPromptHowReach: '¿Cómo llego a Gran Vía desde aquí?',
    quickActionRoadworks: '🚧 ¿Hay obras en mi línea?',
    quickActionPromptRoadworks: '¿Hay alguna incidencia activa cerca de aquí?',
  },

  en: {
    tagline: 'Smart mobility assistant',
    welcomeMessage: "Hi, I'm Navi! Ask me about any line or stop near Puerta del Sol.",
    inputPlaceholder: 'E.g.: how long until the 27 arrives?',
    inputLabel: 'Type your question about buses',
    askButton: 'Ask',
    loadingMessage: 'Navi is checking…',
    errorMessage: "I couldn't fetch the data right now. Please try again in a few seconds.",
    footerNote: 'Real-time information from EMT Madrid and mobility partners',
    skipLink: 'Skip to main content',

    voiceAsk: 'Ask by voice',
    voiceStop: 'Stop voice recording',
    voiceErrorPermission: 'I need microphone permission.',
    voiceErrorNoSpeech: "I didn't hear anything, try again.",
    voiceErrorGeneric: "I couldn't hear you, try again.",

    settingsTrigger: 'Preferences',
    settingsAppearance: 'Appearance',
    themeLight: 'Light',
    themeDark: 'Dark',
    themeHighContrast: 'High contrast',
    settingsFontSize: 'Text size',
    fontSizeNormal: 'Normal',
    fontSizeLarge: 'Large',
    fontSizeXLarge: 'Extra large',
    settingsLanguage: 'Language',

    statusBusComing: 'Bus on the way',
    statusNoBus: 'No upcoming bus',
    statusAlert: 'Active disruption',
    statusStale: 'Outdated data',
    statusTerminus: 'Terminus stop',
    nextBusIn: (min) => `Next bus in ${min} min`,
    nextAfter: (min) => `next in ${min} min`,
    moreInfo: 'More info',
    freqWeekday: 'Weekday frequency',
    freqEvery: (min) => `every ${min} min`,
    freqUnknown: "I don't have that data yet",

    heroTitle: "Hi! I'm Navi 👋",
    heroSubtitle: 'How can I help you get around today?',
    quickActionNextBus: '🚌 Upcoming buses',
    quickActionPromptNextBus: 'What buses are arriving at my stop now?',
    quickActionHowReach: '📍 How do I get to Gran Vía?',
    quickActionPromptHowReach: 'How do I get to Gran Vía from here?',
    quickActionRoadworks: '🚧 Roadworks on my line?',
    quickActionPromptRoadworks: 'Is there any active disruption near here?',
  },

  pt: {
    tagline: 'Seu assistente inteligente de mobilidade',
    welcomeMessage: 'Olá, sou o Navi! Pergunte sobre qualquer linha ou parada perto de Puerta del Sol.',
    inputPlaceholder: 'Ex: quanto tempo falta para a linha 27?',
    inputLabel: 'Escreva sua pergunta sobre ônibus',
    askButton: 'Perguntar',
    loadingMessage: 'Navi está consultando…',
    errorMessage: 'Não consegui consultar os dados agora. Tente novamente em alguns segundos.',
    footerNote: 'Informações em tempo real da EMT Madrid e parceiros de mobilidade',
    skipLink: 'Pular para o conteúdo principal',

    voiceAsk: 'Perguntar por voz',
    voiceStop: 'Parar gravação de voz',
    voiceErrorPermission: 'Preciso de permissão para usar o microfone.',
    voiceErrorNoSpeech: 'Não ouvi nada, tente novamente.',
    voiceErrorGeneric: 'Não consegui te ouvir, tente novamente.',

    settingsTrigger: 'Preferências',
    settingsAppearance: 'Aparência',
    themeLight: 'Claro',
    themeDark: 'Escuro',
    themeHighContrast: 'Alto contraste',
    settingsFontSize: 'Tamanho do texto',
    fontSizeNormal: 'Normal',
    fontSizeLarge: 'Grande',
    fontSizeXLarge: 'Muito grande',
    settingsLanguage: 'Idioma',

    statusBusComing: 'Ônibus a caminho',
    statusNoBus: 'Sem ônibus próximo',
    statusAlert: 'Incidência ativa',
    statusStale: 'Dado desatualizado',
    statusTerminus: 'Parada terminal',
    nextBusIn: (min) => `Próximo ônibus em ${min} min`,
    nextAfter: (min) => `próximo em ${min} min`,
    moreInfo: 'Mais informações',
    freqWeekday: 'Frequência em dias úteis',
    freqEvery: (min) => `a cada ${min} min`,
    freqUnknown: 'ainda não tenho esse dado',

    heroTitle: 'Olá! Eu sou o NAVI 👋',
    heroSubtitle: 'Como posso te ajudar a se mover hoje?',
    quickActionNextBus: '🚌 Próximos ônibus',
    quickActionPromptNextBus: 'Quais ônibus chegam agora na minha parada?',
    quickActionHowReach: '📍 Como chegar a Gran Vía?',
    quickActionPromptHowReach: 'Como chego a Gran Vía a partir daqui?',
    quickActionRoadworks: '🚧 Há obras na minha linha?',
    quickActionPromptRoadworks: 'Há alguma incidência ativa perto daqui?',
  },
};

export const SUPPORTED_LANGUAGES = [
  { code: 'es', label: 'Español' },
  { code: 'en', label: 'English' },
  { code: 'pt', label: 'Português' },
];

export function detectDefaultLanguage() {
  const browserLang = (navigator.language || 'es').slice(0, 2);
  const supported = SUPPORTED_LANGUAGES.map((l) => l.code);
  return supported.includes(browserLang) ? browserLang : 'es';
}
