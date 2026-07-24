// services/naviAgent.js
//
// ⚠️ ÚNICO ARCHIVO A CAMBIAR cuando el Data Agent esté publicado como MCP.
//
// Contrato de retorno: { answerText: string, rows: GoldRow[] }
// `language` ('es' | 'en' | 'pt') se recibe para que el mock responda
// coherente con la UI. Cuando conecten el Data Agent real, pasar este mismo
// parámetro en el payload del MCP para que responda en el idioma correcto —
// no está confirmado en el contrato de datos si el agente real lo soporta,
// hay que validarlo con quien configure el Data Agent.

// import { mockGoldRows } from '../mocks/mockGoldRows';

// const SIMULATED_LATENCY_MS = 600;

// const ANSWERS = {
//   incident: {
//     es: (line, header) => `La línea ${line} tiene una incidencia activa: ${header}.`,
//     en: (line, header) => `Line ${line} has an active disruption: ${header}.`,
//     pt: (line, header) => `A linha ${line} tem uma incidência ativa: ${header}.`,
//   },
//   stale: {
//     es: (line) => `El dato de la línea ${line} podría estar desactualizado, pero el último bus visto llega en unos minutos.`,
//     en: (line) => `Data for line ${line} might be outdated, but the last bus seen arrives in a few minutes.`,
//     pt: (line) => `O dado da linha ${line} pode estar desatualizado, mas o último ônibus visto chega em poucos minutos.`,
//   },
//   noBus: {
//     es: (line) => `No veo ningún autobús próximo de la línea ${line} en esta parada ahora mismo.`,
//     en: (line) => `I don't see any upcoming bus for line ${line} at this stop right now.`,
//     pt: (line) => `Não vejo nenhum ônibus próximo da linha ${line} nesta parada agora.`,
//   },
//   allLines: {
//     es: 'Estas son las líneas que pasan cerca de tu ubicación:',
//     en: 'Here are the lines passing near your location:',
//     pt: 'Estas são as linhas que passam perto da sua localização:',
//   },
// };

// export async function askNaviAgent(userQuestion, language = 'es') {
  // ============================================================
  // TODO (cuando el Data Agent esté publicado): reemplazar el cuerpo
  // por un fetch real a import.meta.env.VITE_NAVI_MCP_URL, incluyendo
  // { question: userQuestion, language } en el payload.
  // ============================================================

  // await new Promise((resolve) => setTimeout(resolve, SIMULATED_LATENCY_MS));

  // const lang = ANSWERS.allLines[language] ? language : 'es';
  // const q = userQuestion.toLowerCase();

  // if (q.includes('incidencia') || q.includes('incident') || q.includes('14')) {
  //   const row = mockGoldRows.find((r) => r.line_id === '014');
  //   return { answerText: ANSWERS.incident[lang](row.line_label, row.alert_header), rows: [row] };
  // }
  // if (q.includes('51') || q.includes('aluche')) {
  //   const row = mockGoldRows.find((r) => r.line_id === '051');
  //   return { answerText: ANSWERS.stale[lang](row.line_label), rows: [row] };
  // }
  // if (q.includes('3') && !q.includes('27') && !q.includes('51')) {
  //   const row = mockGoldRows.find((r) => r.line_id === '003');
  //   return { answerText: ANSWERS.noBus[lang](row.line_label), rows: [row] };
  // }
  // return { answerText: ANSWERS.allLines[lang], rows: mockGoldRows };

  // services/naviAgent.js

import { getRayfinClient } from './rayfinClient';

const MCP_URL = import.meta.env.VITE_NAVI_MCP_URL;

const MCP_TOOL = 'DataAgent_emt_specialist_agent';

export async function askNaviAgent(userQuestion, language = 'es') {
  if (!MCP_URL) {
    throw new Error('VITE_NAVI_MCP_URL no está configurada.');
  }

  const client = getRayfinClient();

  const session = client.auth.getSession();

  if (!session?.accessToken) {
    throw new Error('No hay sesión Fabric activa.');
  }

  const response = await fetch(MCP_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${session.accessToken}`,
    },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: Date.now(),
      method: 'tools/call',
      params: {
        name: MCP_TOOL,
        arguments: {
          question: userQuestion,
          language,
        },
      },
    }),
  });

  if (!response.ok) {
    throw new Error(
      `Error llamando al Data Agent MCP: ${response.status}`
    );
  }

  const result = await response.json();

  const text =
    result?.result?.content?.[0]?.text ??
    'No se recibió respuesta del agente.';

  return {
    answerText: text,
    rows: [],
  };
}
