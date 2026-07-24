export interface ChatRequest {
  question: string;
  language: string;
}

export interface ChatResponse {
  answerText: string;
  rows?: Record<string, unknown>[];
}

export async function askAgent(question: string, language = 'es'): Promise<ChatResponse> {
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, language }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend local /api/chat no responde. Usando respuesta Mock local:', err);
    return {
      answerText: `[Modo Prueba] La línea 027 pasará por la parada de Lavapiés en aproximadamente 3 minutos.`,
      rows: [
        { linea: '027', parada: 'LAVAPIES', tiempo_estimado: '3 min', destino: 'EMBAJADORES' }
      ]
    };
  }
}