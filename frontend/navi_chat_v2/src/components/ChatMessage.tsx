import type { ChatResponse } from '@/services/agentService';

interface ChatMessageProps {
  role: 'user' | 'agent';
  text: string;
  rows?: Record<string, unknown>[];
}

export default function ChatMessage({ role, text, rows }: ChatMessageProps) {
  return (
    <div
      className={`flex items-start gap-2 ${
        role === 'user' ? 'flex-row-reverse self-end' : 'self-start'
      }`}
      style={{ maxWidth: '85%' }}
    >
      {role === 'agent' && (
        <span className="flex-shrink-0 w-8 h-8 rounded-full overflow-hidden bg-[#eef6f3] flex items-center justify-center">
          <img
            src="/navi-mascot.svg"
            alt=""
            className="w-full h-full object-cover"
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).style.display = 'none';
            }}
          />
        </span>
      )}
      <div
        className={`rounded-2xl px-4 py-3 ${
          role === 'user'
            ? 'bg-[#f0f0f0] text-[#1a1a1a]'
            : 'bg-[#eef6f3] text-[#1a1a1a]'
        }`}
      >
        <p className="m-0 text-sm leading-relaxed whitespace-pre-wrap">{text}</p>
        {rows && rows.length > 0 && (
          <div className="mt-3 flex flex-col gap-3">
            {rows.map((row, i) => (
              <div
                key={i}
                className="chat-card flex flex-col gap-2 rounded-xl border border-gray-300 bg-white p-3.5 text-gray-900 shadow-sm transition-all"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[#0072B2] text-sm font-bold text-white border border-white">
                    {String(row.linea || row.line_id || '27')}
                  </div>
                  <div className="flex flex-col leading-tight">
                    <span className="font-semibold text-sm text-gray-900">
                      {String(row.parada || row.stop_name || 'Puerta del Sol')}
                    </span>
                    <span className="text-xs text-gray-700">
                      hacia {String(row.destino || row.direction || 'Plaza de Castilla')}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs">
                  <span className="rounded-full bg-[#00875A] px-3 py-1 font-medium text-white">
                    • Próximo bus en {String(row.tiempo_estimado || row.estimated_arrival || '3 min')}
                  </span>
                  <span className="text-gray-700">
                    • próximo en {String(row.siguiente_bus || '9 min')}
                  </span>
                </div>

                <div className="text-[11px] text-gray-700">
                  Frecuencia en días laborables: a cada {String(row.frecuencia || '8 min')}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}