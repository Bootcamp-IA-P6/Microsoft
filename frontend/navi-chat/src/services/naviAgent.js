// services/naviAgent.js
import { mockGoldRows } from '../mocks/mockGoldRows';

export async function askNaviAgent(userQuestion, language = 'es') {
  const mcpUrl = import.meta.env.VITE_NAVI_MCP_URL;

  // Si no hay URL configurada en el .env, hace fallback al mock por seguridad
  if (!mcpUrl) {
    console.warn("⚠️ VITE_NAVI_MCP_URL no está definida. Usando respuesta mock.");
    return {
      answerText: "Modo Mock: La línea 027 llegará en 3 mins.",
      rows: mockGoldRows
    };
  }

  try {
    const response = await fetch(mcpUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: userQuestion,
        language: language
      })
    });

    if (!response.ok) {
      throw new Error(`Error en el Data Agent: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();

    // Normalizamos la respuesta del Agente para que coincida con lo que espera React
    return {
      answerText: data.answerText || data.response || "Respuesta recibida del agente.",
      rows: data.rows || data.data || [] // Si el agente no devuelve la lista de buses, pasa un array vacío
    };

  } catch (error) {
    console.error("❌ Error al conectar con Navi Data Agent:", error);
    
    // Retorno de fallback ante fallos de red para no romper la app
    return {
      answerText: `No se pudo conectar con el asistente (${error.message}). Por favor, reintenta en un momento.`,
      rows: []
    };
  }
}