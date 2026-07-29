import { getStopCoords } from '@/utils/geoData';
import { parseBusInfo, isBusRelated } from '@/utils/parseBusInfo';
import BusCard from './BusCard';
import NaviMascot from './NaviMascot'; // === NAVI-MAP: reemplaza el <img navi-mascot.svg> por tu componente ===

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
    <div className={`chat-message ${role === 'user' ? 'chat-message--user' : 'chat-message--agent'}`}>
      {role === 'agent' && (
        <span className="chat-message__avatar">
          <NaviMascot size={32} />
        </span>
      )}
      <div className="chat-message__body">
        <p className="chat-message__text">{text}</p>

        {showBusCard && busInfo && (
          <div className="chat-message__rows">
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
          <div className="chat-message__stops">
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
                  className="action-chip"
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
