export interface ChatRequest {
  question: string;
  language: string;
}

export interface ChatResponse {
  answerText: string;
}

export async function askAgent(question: string, language = 'es'): Promise<ChatResponse> {
  const backendUrl = import.meta.env.VITE_CHAT_BACKEND_URL;
  const apiKey = import.meta.env.VITE_DEMO_API_KEY;

  if (backendUrl && apiKey) {
    try {
      const res = await fetch(`${backendUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Demo-Key': apiKey },
        body: JSON.stringify({ question, language }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn('Backend real no responde. Usando respuesta Mock local:', err);
    }
  }

  return {
    answerText:
      language === 'es'
        ? `[Modo Prueba] La línea 027 pasará por la parada de Lavapiés en aproximadamente 3 minutos.`
        : `[Mock Mode] Bus line 027 will arrive at Lavapiés stop in approximately 3 minutes.`,
  };
}