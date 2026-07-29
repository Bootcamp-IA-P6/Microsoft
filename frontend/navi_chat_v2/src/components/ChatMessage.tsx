import { getStopCoords } from '@/utils/geoData';
import { stopById } from '@/utils/stopsFromGold';
import { parseBusInfo, isBusRelated } from '@/utils/parseBusInfo';
import type { MapData } from '@/services/agentService';
import BusCard from './BusCard';
import NaviMascot from './NaviMascot';

interface ChatMessageProps {
  messageId: string;
  role: 'user' | 'agent';
  text: string;
  matchedStops?: string[];
  timestamp?: number;
  feedback?: 'like' | 'dislike' | null;
  feedbackSent?: boolean;
  onFeedback?: (messageId: string, feedback: 'like' | 'dislike') => void;
  key?: string | number;
  mapData?: MapData | null;
  agentMeta?: { stop_id?: string; stop_name?: string; line_number?: string; wait_time?: string };
}

function formatTime(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function ChatMessage({ messageId, role, text, matchedStops, timestamp, feedback, feedbackSent, onFeedback, mapData, agentMeta }: ChatMessageProps) {
  const busInfo = role === 'agent' ? parseBusInfo(text) : null;
  const showBusCard = busInfo && isBusRelated(text);

  // Override parseBusInfo results with structured metadata from the agent when available
  if (showBusCard && busInfo && agentMeta) {
    if (agentMeta.stop_name) busInfo.stopName = agentMeta.stop_name;
    if (agentMeta.line_number) busInfo.line = agentMeta.line_number;
  }

  // Si ya hay BusCard con botón flyTo, no mostrar el botón duplicado de mapData
  const showMapButton = role === 'agent' && mapData?.stop_coordinates && !showBusCard;
  // Si ya hay BusCard, no mostrar action-chips de paradas (evita duplicación)
  const showStopChips = matchedStops && matchedStops.length > 0 && !showBusCard;

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
                // Resolver stop_id del texto para obtener coords y nombre correctos
                const textStopId = text.match(/parada\s+(\d{3,5})/i)?.[1];
                const resolvedStop = textStopId ? stopById[textStopId] : undefined;

                // Prioridad: stopById coords > mapData coords > matchedStops coords
                const coords = resolvedStop
                  ? [resolvedStop.lon, resolvedStop.lat] as [number, number]
                  : mapData?.stop_coordinates
                    || (matchedStops && matchedStops.length > 0 ? getStopCoords(matchedStops[0]) : null);

                const stopName = resolvedStop?.stop_name
                  || agentMeta?.stop_name
                  || busInfo.stopName
                  || '';

                if (coords) {
                  window.dispatchEvent(
                    new CustomEvent('map:showRoute', {
                      detail: {
                        stopCoordinates: coords,
                        stopName,
                        stopId: textStopId || '',
                        lineLabel: agentMeta?.line_number || busInfo.line || '',
                      },
                    })
                  );
                  window.dispatchEvent(
                    new CustomEvent('nav:changeView', { detail: { view: 'split' } })
                  );
                }
              }}
            />
          </div>
        )}

        {showStopChips && (
          <div className="chat-message__stops">
            {matchedStops!.map((stop, i) => {
              const coords = getStopCoords(stop);
              if (!coords) return null;

              return (
                <button
                  key={i}
                  type="button"
                  onClick={() => {
                    window.dispatchEvent(
                      new CustomEvent('map:flyTo', { detail: { lng: coords[0], lat: coords[1], zoom: 16, stopName: stop } })
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

        {showMapButton && (
          <div style={{ marginTop: '0.5rem' }}>
            <button
              type="button"
              className="action-chip"
              onClick={() => {
                window.dispatchEvent(new CustomEvent('map:showRoute', {
                  detail: {
                    stopCoordinates: mapData.stop_coordinates,
                    stopName: matchedStops?.[0] || '',
                    lineLabel: '',
                  },
                }));
                window.dispatchEvent(new CustomEvent('nav:changeView', { detail: { view: 'split' } }));
              }}
            >
              Ver ubicación en mapa 3D →
            </button>
          </div>
        )}

        {role === 'agent' && timestamp && (
          <div className="chat-message__footer">
            <span className="chat-message__time">{formatTime(timestamp)}</span>
            <div className="chat-message__feedback">
              {feedbackSent ? (
                <span className="chat-message__fb-sent">✓</span>
              ) : (
                <>
                  <button
                    type="button"
                    className={`chat-message__fb-btn ${feedback === 'like' ? 'chat-message__fb-btn--like' : ''}`}
                    onClick={() => onFeedback?.(messageId, 'like')}
                    aria-label="Like"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill={feedback === 'like' ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    className={`chat-message__fb-btn ${feedback === 'dislike' ? 'chat-message__fb-btn--dislike' : ''}`}
                    onClick={() => onFeedback?.(messageId, 'dislike')}
                    aria-label="Dislike"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill={feedback === 'dislike' ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10zM17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
                    </svg>
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
