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
}

export interface ChatResponse {
  chat_message: ChatMessageData;
  map_data: MapData | null;
}

/**
 * Extrae metadatos estructurados (stop_id, stop_name, line_number, wait_time)
 * que el agente incluye como texto plano, y los elimina del texto visible.
 * Soporta formatos:
 *   stop_id: 5907
 *   - stop_id: 5907
 *   * stop_id: 5907
 */
function extractMetadataFromText(rawText: string): {
  cleanText: string;
  stop_id?: string;
  stop_name?: string;
  line_number?: string;
  wait_time?: string;
} {
  const metadata: Record<string, string> = {};
  const metaKeys = ['stop_id', 'stop_name', 'line_number', 'wait_time'];

  let cleanText = rawText;
  for (const key of metaKeys) {
    // Match: optional list marker (- or *), then key: value
    const regex = new RegExp(`^\\s*[-*]?\\s*${key}\\s*[:=]\\s*(.+)$`, 'gim');
    let match: RegExpExecArray | null;
    while ((match = regex.exec(cleanText)) !== null) {
      metadata[key] = match[1].trim();
    }
    // Remove the metadata lines from visible text
    cleanText = cleanText.replace(new RegExp(`^\\s*[-*]?\\s*${key}\\s*[:=]\\s*.+$`, 'gim'), '');
  }

  // Clean up excess blank lines left behind
  cleanText = cleanText.replace(/\n{3,}/g, '\n\n').trim();

  return {
    cleanText,
    stop_id: metadata['stop_id'],
    stop_name: metadata['stop_name'],
    line_number: metadata['line_number'],
    wait_time: metadata['wait_time'],
  };
}

function parseChatResponse(responseData: unknown): ChatResponse {
  const output = (responseData as any)?.output || (responseData as any)?.result || responseData;

  const chatMessage = output?.chat_message;
  if (chatMessage?.text) {
    const extracted = extractMetadataFromText(chatMessage.text);
    return {
      chat_message: {
        text: extracted.cleanText,
        stop_id: chatMessage.stop_id || extracted.stop_id,
        stop_name: chatMessage.stop_name || extracted.stop_name,
        line_number: chatMessage.line_number || extracted.line_number,
        wait_time: chatMessage.wait_time || extracted.wait_time,
      },
      map_data: output?.map_data ?? null,
    };
  }

  const answerText = output?.answerText as string | undefined;
  if (answerText) {
    const extracted = extractMetadataFromText(answerText);
    return {
      chat_message: {
        text: extracted.cleanText,
        stop_id: extracted.stop_id,
        stop_name: extracted.stop_name,
        line_number: extracted.line_number,
        wait_time: extracted.wait_time,
      },
      map_data: null,
    };
  }

  throw new Error('UDF respondió sin contenido válido');
}

export async function sendFeedbackToFabric(
  messageId: string,
  feedbackType: string,
  question: string,
  answerText: string,
) {
  const udfUrl = import.meta.env.VITE_UDF_PUBLIC_URL;
  if (!udfUrl) {
    throw new Error('VITE_UDF_PUBLIC_URL no está configurada');
  }
  const url = new URL(udfUrl);
  const segments = url.pathname.split('/').filter(Boolean);
  segments[segments.length - 2] = 'save_feedback';
  url.pathname = '/' + segments.join('/');
  const feedbackUrl = url.toString();

  try {
    const payload = {
      messageid: messageId,
      timestamp: Date.now().toString(),
      feedbacktype: feedbackType,
      question,
      answertext: answerText,
    };

    const { acquireToken } = await import('./udfAuth');
    const token = await acquireToken();

    const res = await fetch(feedbackUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error(`Error en el servidor: ${res.statusText}`);
    }

    const result = await res.json();
    console.log('[FEEDBACK ENVIADO A FABRIC]:', result);
    return result;
  } catch (error) {
    console.error('[ERROR ENVIANDO FEEDBACK]:', error);
  }
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