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
    tagline: 'Tu asistente inteligente de movilidad',
    heroTitle: 'NAVI, tu copiloto urbano',
    heroSubtitle: 'Consulta horarios, recorridos y avisos de la ciudad en un chat rápido y confiable.',
    welcomeMessage: 'Hola, soy NAVI! Pregúntame por cualquier línea o parada cerca de Puerta del Sol.',
    inputPlaceholder: 'Ej: ¿cuánto tarda la línea 27?',
    inputLabel: 'Escribe tu pregunta sobre buses',
    askButton: 'Preguntar',
    loadingMessage: 'Navi está consultando…',
    errorMessage: 'No pude consultar los datos en este momento. Intenta de nuevo en unos segundos.',
    footerNote: 'Datos EMT Madrid · zona Puerta del Sol (600m)',
    skipLink: 'Saltar al contenido principal',

    voiceAsk: 'Preguntar por voz',
    quickActionNextBus: 'Próximos ómnibus',
    quickActionPromptNextBus: 'Próximos autobuses en Puerta del Sol',
    quickActionHowReach: 'Cómo llegar al trabajo?',
    quickActionPromptHowReach: 'Cómo llegar al trabajo desde Puerta del Sol',
    quickActionRoadworks: '¿Hay obras en mi línea?',
    quickActionPromptRoadworks: '¿Hay obras en mi línea de bus?',
    chatPlaceholder: 'Aquí aparecerán las respuestas del asistente.',
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
  },

  en: {
    tagline: 'Your smart mobility assistant',
    heroTitle: 'NAVI, your urban copilot',
    heroSubtitle: 'Check schedules, routes, and service alerts from one fast chat.',
    welcomeMessage: "Hi, I'm NAVI! Ask me about any line or stop near Puerta del Sol.",
    inputPlaceholder: 'E.g.: how long until the 27 arrives?',
    inputLabel: 'Type your question about buses',
    askButton: 'Ask',
    loadingMessage: 'Navi is checking…',
    errorMessage: "I couldn't fetch the data right now. Please try again in a few seconds.",
    footerNote: 'EMT Madrid data · Puerta del Sol area (600m)',
    skipLink: 'Skip to main content',

    voiceAsk: 'Ask by voice',
    quickActionNextBus: 'Next buses',
    quickActionPromptNextBus: 'Next buses at Puerta del Sol',
    quickActionHowReach: 'How to get to work?',
    quickActionPromptHowReach: 'How to get to work from Puerta del Sol',
    quickActionRoadworks: 'Any works on my line?',
    quickActionPromptRoadworks: 'Any roadworks on my bus line?',
    chatPlaceholder: 'Assistant responses will appear here.',
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
  },

  pt: {
    tagline: 'Seu assistente inteligente de mobilidade',
    heroTitle: 'NAVI, seu copiloto urbano',
    heroSubtitle: 'Consulte horários, rotas e avisos da cidade em um chat rápido.',
    welcomeMessage: 'Olá, sou o NAVI! Pergunte sobre qualquer linha ou parada perto de Puerta del Sol.',
    inputPlaceholder: 'Ex: quanto tempo falta para a linha 27?',
    inputLabel: 'Escreva sua pergunta sobre ônibus',
    askButton: 'Perguntar',
    loadingMessage: 'Navi está consultando…',
    errorMessage: 'Não consegui consultar os dados agora. Tente novamente em alguns segundos.',
    footerNote: 'Dados EMT Madrid · região Puerta del Sol (600m)',
    skipLink: 'Pular para o conteúdo principal',

    voiceAsk: 'Perguntar por voz',
    quickActionNextBus: 'Próximos ônibus',
    quickActionPromptNextBus: 'Próximos ônibus em Puerta del Sol',
    quickActionHowReach: 'Como chegar ao trabalho?',
    quickActionPromptHowReach: 'Como chegar ao trabalho desde Puerta del Sol',
    quickActionRoadworks: 'Há obras na minha linha?',
    quickActionPromptRoadworks: 'Há obras na minha linha de ônibus?',
    chatPlaceholder: 'As respostas do assistente aparecerão aqui.',
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
