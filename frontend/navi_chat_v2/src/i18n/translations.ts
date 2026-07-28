// i18n/translations.ts
//
// === FUSIÓN ===
// Este archivo antes era DOS archivos distintos (uno de tu compi, con
// tipo Lang + t()/speechLang() usado por ChatContainer.tsx y Map.tsx; y
// tu i18n/translations.js viejo, usado por LanguageContext.jsx con
// SUPPORTED_LANGUAGES + detectDefaultLanguage()). Los fusioné en uno
// solo porque los dos importan desde la MISMA ruta ('@/i18n/translations'
// / '../i18n/translations') y eso es lo que rompía el build.
//
// Regla para agregar strings nuevos: cada clave nueva va en las 4
// columnas (es/en/pt/ko). Si falta una traducción para un idioma,
// t() (de tu compi) cae de vuelta a mostrar la propia clave; tu
// LanguageContext, según el comentario que tenías, cae al español.

export type Lang = 'es' | 'en' | 'pt' | 'ko';

export const translations: Record<Lang, Record<string, string>> = {
  es: {
    // ---- claves de tu compi (ChatContainer / Map / App — tabs) ----
    title: 'NAVI',
    tabChat: 'Chat',
    tabMap: 'Mapa 3D',
    tabSplit: 'Dividida',
    greeting: '¡Hola! Soy NAVI',
    subtitle: 'Pregúntame sobre llegadas de autobús en Madrid',
    quickC1Bus: 'Línea C1 en Gran Vía',
    quickC1BusPrompt: '¿Cuánto tarda el próximo bus de la línea C1 en Gran Vía?',
    quickCibeles: 'Buses en Cibeles',
    quickCibelesPrompt: '¿Qué buses llegan ahora mismo a la parada de Cibeles?',
    quickLine27: 'Incidencia línea 27',
    quickLine27Prompt: '¿Hay alguna incidencia o desvío activo en la línea 27?',
    quickM1Freq: 'Frecuencia línea M1',
    quickM1FreqPrompt: '¿Cada cuánto tiempo pasa la línea M1 en hora punta?',
    // === FUSIÓN: 'inputPlaceholder' existía en los dos archivos con texto
    // distinto. Gana el de tu compi porque es el que ChatContainer.tsx
    // muestra literalmente en el input — no quería cambiarle el texto a
    // algo que ya está funcionando. ===
    inputPlaceholder: 'Ej: ¿Cuánto tarda el próximo bus en Lavapiés?',
    send: 'Enviar',
    loading: 'Pensando',
    error: 'Lo siento, hubo un error al procesar tu consulta. Intenta de nuevo.',
    mapLabel: 'Madrid — Mapa 3D',
    themeLabel: 'Alto Contraste',
    langLabel: 'Idioma',

    // ---- claves tuyas (navbar / App.tsx / estado vacío) ----
    tagline: 'Asistente inteligente de movilidad',
    welcomeMessage: 'Hola, soy Navi! Pregúntame por cualquier línea o parada cerca de Puerta del Sol.',
    inputLabel: 'Escribe tu pregunta sobre buses',
    askButton: 'Preguntar',
    loadingMessage: 'Navi está consultando…',
    errorMessage: 'No pude consultar los datos en este momento. Intenta de nuevo en unos segundos.',
    footerNote: 'Información en tiempo real de EMT Madrid',
    skipLink: 'Saltar al contenido principal',
    // === FUSIÓN: 'settings' no existía en ninguno de los dos archivos —
    // tu App.tsx llama a t('settings') para el aria-label del botón ⚙️
    // pero esa clave nunca estuvo definida. La agrego para que no se
    // muestre la clave cruda "settings" en pantallas chicas. ===
    settings: 'Ajustes',

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
    themeNormal: 'Normal',
    settingsTheme: 'Contraste',
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
    moreInfo: 'Más información',
    freqWeekday: 'Frecuencia laborable',
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
    title: 'NAVI',
    tabChat: 'Chat',
    tabMap: '3D Map',
    tabSplit: 'Split',
    greeting: "Hello! I'm NAVI",
    subtitle: 'Ask me about bus arrivals in Madrid',
    quickC1Bus: 'C1 bus at Gran Vía',
    quickC1BusPrompt: 'How long until the next C1 bus at Gran Vía?',
    quickCibeles: 'Buses at Cibeles',
    quickCibelesPrompt: 'Which buses are arriving at Cibeles right now?',
    quickLine27: 'Line 27 disruptions',
    quickLine27Prompt: 'Are there any active disruptions on line 27?',
    quickM1Freq: 'M1 frequency',
    quickM1FreqPrompt: 'How often does line M1 run during rush hour?',
    inputPlaceholder: 'e.g. When is the next bus at Lavapiés?',
    send: 'Send',
    loading: 'Thinking',
    error: 'Sorry, there was an error processing your request. Please try again.',
    mapLabel: 'Madrid — 3D Map',
    themeLabel: 'High Contrast',
    langLabel: 'Language',

    tagline: 'Your smart mobility assistant',
    welcomeMessage: "Hi, I'm Navi! Ask me about any line or stop near Puerta del Sol.",
    inputLabel: 'Type your question about buses',
    askButton: 'Ask',
    loadingMessage: 'Navi is checking…',
    errorMessage: "I couldn't fetch the data right now. Please try again in a few seconds.",
    footerNote: 'Real-time information from EMT Madrid and mobility partners',
    skipLink: 'Skip to main content',
    settings: 'Settings',

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
    themeNormal: 'Normal',
    settingsTheme: 'Contrast',
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
    moreInfo: 'More info',
    freqWeekday: 'Weekday frequency',
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
    title: 'NAVI',
    tabChat: 'Chat',
    tabMap: 'Mapa 3D',
    tabSplit: 'Dividida',
    greeting: 'Olá! Sou o NAVI',
    subtitle: 'Pergunte-me sobre chegadas de autocarros em Madrid',
    quickC1Bus: 'Autocarro C1 na Gran Vía',
    quickC1BusPrompt: 'Quanto tempo demora o próximo autocarro C1 na Gran Vía?',
    quickCibeles: 'Autocarros em Cibeles',
    quickCibelesPrompt: 'Que autocarros chegam agora a Cibeles?',
    quickLine27: 'Incidências linha 27',
    quickLine27Prompt: 'Há alguma incidência ou desvio ativo na linha 27?',
    quickM1Freq: 'Frequência linha M1',
    quickM1FreqPrompt: 'Com que frequência passa a linha M1 na hora de ponta?',
    inputPlaceholder: 'Ex: Quando chega o próximo autocarro em Lavapiés?',
    send: 'Enviar',
    loading: 'A pensar',
    error: 'Desculpe, ocorreu um erro ao processar a sua consulta. Tente novamente.',
    mapLabel: 'Madrid — Mapa 3D',
    themeLabel: 'Alto Contraste',
    langLabel: 'Idioma',

    tagline: 'Seu assistente inteligente de mobilidade',
    welcomeMessage: 'Olá, sou o Navi! Pergunte sobre qualquer linha ou parada perto de Puerta del Sol.',
    inputLabel: 'Escreva sua pergunta sobre ônibus',
    askButton: 'Perguntar',
    loadingMessage: 'Navi está consultando…',
    errorMessage: 'Não consegui consultar os dados agora. Tente novamente em alguns segundos.',
    footerNote: 'Informações em tempo real da EMT Madrid e parceiros de mobilidade',
    skipLink: 'Pular para o conteúdo principal',
    settings: 'Configurações',

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
    themeNormal: 'Normal',
    settingsTheme: 'Contraste',
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
    moreInfo: 'Mais informações',
    freqWeekday: 'Frequência em dias úteis',
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

  ko: {
    // Ya existían en el archivo de tu compi:
    title: 'NAVI',
    tabChat: '채팅',
    tabMap: '3D 지도',
    tabSplit: '분할',
    greeting: '안녕하세요! NAVI입니다',
    subtitle: '마드리드 버스 도착 정보를 물어보세요',
    quickC1Bus: '그란 비아 C1 버스',
    quickC1BusPrompt: '그란 비아에서 다음 C1 버스가 얼마나 걸리나요?',
    quickCibeles: '시벨레스 정류장 버스',
    quickCibelesPrompt: '지금 시벨레스 정류장에 도착하는 버스는 무엇인가요?',
    quickLine27: '27번 노선 운행 정보',
    quickLine27Prompt: '27번 노선에 현재 운행 지연이나 우회 구간이 있나요?',
    quickM1Freq: 'M1 노선 배차 간격',
    quickM1FreqPrompt: '출퇴근 시간에 M1 노선은 얼마나 자주 오나요?',
    inputPlaceholder: '예: Lavapiés 정류장 다음 버스는?',
    send: '전송',
    loading: '생각 중',
    error: '죄송합니다. 요청 처리 중 오류가 발생했습니다. 다시 시도해주세요.',
    mapLabel: '마드리드 — 3D 지도',
    themeLabel: '고대비',
    langLabel: '언어',

    // === FUSIÓN: estas no existían en ko — las agrego ahora para que tu
    // navbar/estado vacío también salgan en coreano, no solo el chat. ===
    tagline: '스마트 모빌리티 어시스턴트',
    welcomeMessage: '안녕하세요, NAVI입니다! Puerta del Sol 근처의 노선이나 정류장에 대해 물어보세요.',
    inputLabel: '버스에 대한 질문을 입력하세요',
    askButton: '질문하기',
    loadingMessage: 'NAVI가 확인 중입니다…',
    errorMessage: '지금은 데이터를 가져올 수 없었습니다. 잠시 후 다시 시도해주세요.',
    footerNote: 'EMT 마드리드 실시간 정보',
    skipLink: '본문으로 건너뛰기',
    settings: '설정',

    voiceAsk: '음성으로 질문하기',
    voiceStop: '음성 녹음 중지',
    voiceErrorPermission: '마이크 권한이 필요합니다.',
    voiceErrorNoSpeech: '아무 소리도 들리지 않았어요. 다시 시도해주세요.',
    voiceErrorGeneric: '잘 듣지 못했어요. 다시 시도해주세요.',

    settingsTrigger: '환경설정',
    settingsAppearance: '화면 설정',
    themeLight: '밝게',
    themeDark: '어둡게',
    themeHighContrast: '고대비',
    themeNormal: '보통',
    settingsTheme: '대비',
    settingsFontSize: '글자 크기',
    fontSizeNormal: '보통',
    fontSizeLarge: '크게',
    fontSizeXLarge: '아주 크게',
    settingsLanguage: '언어',

    statusBusComing: '버스 도착 중',
    statusNoBus: '예정된 버스 없음',
    statusAlert: '진행 중인 사고',
    statusStale: '오래된 데이터',
    statusTerminus: '종점',
    moreInfo: '더 알아보기',
    freqWeekday: '평일 배차 간격',
    freqUnknown: '아직 해당 정보가 없습니다',

    heroTitle: '안녕하세요! NAVI입니다 👋',
    heroSubtitle: '오늘 이동을 어떻게 도와드릴까요?',
    quickActionNextBus: '🚌 다음 버스',
    quickActionPromptNextBus: '지금 제 정류장에 도착하는 버스는?',
    quickActionHowReach: '📍 Gran Vía로 가는 방법은?',
    quickActionPromptHowReach: '여기서 Gran Vía까지 어떻게 가나요?',
    quickActionRoadworks: '🚧 제 노선에 공사가 있나요?',
    quickActionPromptRoadworks: '이 근처에 진행 중인 사고가 있나요?',
  },
};

export function t(lang: Lang, key: string): string {
  return translations[lang]?.[key] ?? key;
}

export function speechLang(lang: Lang): string {
  const map: Record<Lang, string> = { es: 'es-ES', en: 'en-US', pt: 'pt-PT', ko: 'ko-KR' };
  return map[lang] ?? 'es-ES';
}

// ---- lo que necesitaba tu LanguageContext.jsx ----

export const SUPPORTED_LANGUAGES = [
  { code: 'es', label: 'Español' },
  { code: 'en', label: 'English' },
  { code: 'pt', label: 'Português' },
  // === FUSIÓN: agregado a pedido tuyo ===
  { code: 'ko', label: '한국어' },
];

export function detectDefaultLanguage() {
  const browserLang = (navigator.language || 'es').slice(0, 2);
  const supported = SUPPORTED_LANGUAGES.map((l) => l.code);
  return supported.includes(browserLang) ? browserLang : 'es';
}
