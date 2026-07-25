import { getStopCoords } from '@/utils/geoData';

interface ChatMessageProps {
  role: 'user' | 'agent';
  text: string;
  matchedStops?: string[];
  key?: string | number;
}

export default function ChatMessage({ role, text, matchedStops }: ChatMessageProps) {
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
        {matchedStops && matchedStops.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {matchedStops.map((stop, i) => {
              const coords = getStopCoords(stop);
              if (!coords) return null;

              return (
                <button
                  key={i}
                  type="button"
                  onClick={() => {
                    window.dispatchEvent(
                      new CustomEvent('map:flyTo', { detail: { lng: coords[0], lat: coords[1], zoom: 16 } })
                    );
                    window.dispatchEvent(
                      new CustomEvent('nav:changeView', { detail: { view: 'split' } })
                    );
                  }}
                  className="inline-flex items-center gap-1.5 rounded-full border border-[#0072B2] bg-white px-3 py-1.5 text-xs font-medium text-[#0072B2] cursor-pointer transition-colors hover:bg-[#0072B2] hover:text-white"
                >
                  📍 {stop}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}