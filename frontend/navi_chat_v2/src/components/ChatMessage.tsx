import { getStopCoords } from '@/utils/geoData';
import { parseBusInfo, isBusRelated } from '@/utils/parseBusInfo';
import BusCard from './BusCard';

interface ChatMessageProps {
  role: 'user' | 'agent';
  text: string;
  matchedStops?: string[];
  key?: string | number;
}

export default function ChatMessage({ role, text, matchedStops }: ChatMessageProps) {
  const busInfo = role === 'agent' ? parseBusInfo(text) : null;
  const showBusCard = busInfo && isBusRelated(text);

  return (
    <div
      className={`flex items-start gap-3 ${
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
      {role === 'user' ? (
        <div className="bg-slate-900 dark:bg-zinc-100 text-white dark:text-zinc-900 rounded-2xl px-4 py-2.5 text-sm md:text-base font-medium">
          <p className="m-0 whitespace-pre-line leading-relaxed">{text}</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-2xl p-4 shadow-sm">
          <p className="m-0 text-slate-800 dark:text-zinc-100 text-sm md:text-base leading-relaxed whitespace-pre-line">{text}</p>
          {showBusCard && busInfo && (
            <div className="mt-4">
              <BusCard
                info={busInfo}
                onFlyTo={() => {
                  if (matchedStops && matchedStops.length > 0) {
                    const coords = getStopCoords(matchedStops[0]);
                    if (coords) {
                      window.dispatchEvent(
                        new CustomEvent('map:flyTo', { detail: { lng: coords[0], lat: coords[1], zoom: 16 } })
                      );
                      window.dispatchEvent(
                        new CustomEvent('nav:changeView', { detail: { view: 'split' } })
                      );
                    }
                  }
                }}
              />
            </div>
          )}
          {matchedStops && matchedStops.length > 0 && (
            <div className="mt-3 pt-3 border-t border-slate-100 dark:border-zinc-800/80 flex flex-wrap gap-2">
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
                    className="inline-flex items-center gap-1.5 bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300 text-xs font-medium px-3 py-1 rounded-full border border-slate-200/50 dark:border-zinc-700/50"
                  >
                    📍 {stop}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}