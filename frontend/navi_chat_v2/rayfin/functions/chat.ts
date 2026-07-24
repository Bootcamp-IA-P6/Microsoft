import type { HttpRequest, HttpResponse } from '@microsoft/rayfin-core';

interface ChatRequest {
  question: string;
  language: string;
}

interface ChatResponse {
  answerText: string;
  rows: Record<string, unknown>[];
}

interface DataAgentResponse {
  answerText?: string;
  response?: string;
  rows?: Record<string, unknown>[];
  data?: Record<string, unknown>[];
}

const isLocalDev = (): boolean =>
  !process.env.DATA_AGENT_URL ||
  process.env.RAYFIN_ENV === 'development' ||
  process.env.NODE_ENV === 'development';

function mockAnswer(question: string, language: string): ChatResponse {
  return {
    answerText:
      language === 'es'
        ? `Modo Mock: La línea 027 llegará a la parada de Lavapiés en 3 minutos.`
        : `Mock Mode: Bus line 027 will arrive at Lavapiés stop in 3 minutes.`,
    rows: [
      {
        line_id: '027',
        stop_id: '1234',
        stop_name: language === 'es' ? 'LAVAPIES' : 'LAVAPIES',
        direction_id: 1,
        direction: language === 'es' ? 'EMB. DE AMÉRICA' : 'EMB. DE AMÉRICA',
        estimated_arrival: '3 min',
        delay: 1,
      },
    ],
  };
}

async function callDataAgent(token: string, question: string, language: string): Promise<DataAgentResponse> {
  const dataAgentUrl = process.env.DATA_AGENT_URL!;

  const response = await fetch(dataAgentUrl, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question, language }),
  });

  if (!response.ok) {
    throw new Error(
      `Data Agent responded with ${response.status}: ${response.statusText}`
    );
  }

  return response.json() as Promise<DataAgentResponse>;
}

export default async function chat(
  request: HttpRequest<ChatRequest>
): Promise<HttpResponse<ChatResponse>> {
  try {
    const { question, language } = request.body;

    if (!question) {
      return { status: 400, body: { answerText: 'Question is required', rows: [] } };
    }

    if (isLocalDev()) {
      return { status: 200, body: mockAnswer(question, language ?? 'es') };
    }

    const { DefaultAzureCredential } = await import('@azure/identity');
    const credential = new DefaultAzureCredential();
    const tokenResponse = await credential.getToken(
      'https://api.fabric.microsoft.com/.default'
    );

    const data = await callDataAgent(tokenResponse.token, question, language ?? 'es');

    return {
      status: 200,
      body: {
        answerText: data.answerText ?? data.response ?? '',
        rows: data.rows ?? data.data ?? [],
      },
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    console.error('[chat function]', message);

    return {
      status: 500,
      body: { answerText: `Error: ${message}`, rows: [] },
    };
  }
}