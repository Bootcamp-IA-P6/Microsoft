export interface ChatMessageData {
  text: string;
  stop_id?: string;
  stop_name?: string;
  line_number?: string;
  wait_time?: string;
}

export interface MapData {
  type: 'bus_stop_and_route';
  stop_coordinates?: [number, number];
  route_geojson?: GeoJSON.Feature<GeoJSON.LineString>;
}

export interface ChatResponse {
  chat_message: ChatMessageData;
  map_data: MapData | null;
}

function parseChatResponse(responseData: unknown): ChatResponse {
  const output = (responseData as any)?.output || (responseData as any)?.result || responseData;

  const chatMessage = output?.chat_message;
  if (chatMessage?.text) {
    return {
      chat_message: {
        text: chatMessage.text,
        stop_id: chatMessage.stop_id,
        stop_name: chatMessage.stop_name,
        line_number: chatMessage.line_number,
        wait_time: chatMessage.wait_time,
      },
      map_data: output?.map_data ?? null,
    };
  }

  const answerText = output?.answerText as string | undefined;
  if (answerText) {
    return {
      chat_message: { text: answerText },
      map_data: null,
    };
  }

  throw new Error('UDF respondió sin contenido válido');
}

export async function askAgent(question: string, language = 'es'): Promise<ChatResponse> {
  const udfUrl = import.meta.env.VITE_UDF_PUBLIC_URL;
  if (!udfUrl) {
    throw new Error('VITE_UDF_PUBLIC_URL no está configurada');
  }

  const { acquireToken } = await import('./udfAuth');
  const token = await acquireToken();

  const payload = { question, language };

  const res = await fetch(udfUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  const responseData = await res.json();

  if (!res.ok) {
    console.error('Error en Fabric UDF:', responseData);
    throw new Error(responseData?.message || 'Error al comunicarse con Fabric UDF');
  }

  return parseChatResponse(responseData);
}