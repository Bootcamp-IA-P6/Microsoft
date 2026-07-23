import { useTranslation } from '../context/LanguageContext';
import BusRowCard from './BusRowCard';

/**
 * @param {{messages?: Array<{id:string, role: 'user' | 'agent', text:string, rows:any[] }>, isLoading?: boolean}} props
 */
export default function ChatWindow({ messages = [], isLoading = false }) {
  const { t } = useTranslation();

  return (
    <section className="chat-window" aria-label="Navi">
      <div className="chat-window__panel">
        <div className="chat-window__log" role="log" aria-live="polite" aria-relevant="additions">
          {messages.length === 0 ? (
            <div className="chat-window__placeholder">
              <p>{t('chatPlaceholder')}</p>
            </div>
          ) : (
            messages.map((msg) => {
              return (
                <div key={msg.id} className={`chat-message chat-message--${msg.role}`}>
                  {msg.role === 'agent' && <span className="chat-message__avatar">🤖</span>}
                  <div className="chat-message__body">
                    <p className="chat-message__text">{msg.text}</p>
                    {msg.rows.length > 0 && (
                      <div className="chat-message__rows">
                        {msg.rows.map((row) => (
                          <BusRowCard
                            key={`${row.stop_id}-${row.line_id}-${row.direction_id}`}
                            row={row}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {isLoading && (
            <p className="chat-message chat-message--agent chat-message--loading" aria-hidden="true">
              {t('loadingMessage')}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
