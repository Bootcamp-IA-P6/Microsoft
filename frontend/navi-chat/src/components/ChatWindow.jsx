import BusRowCard from './BusRowCard';
import NaviMascot from './NaviMascot';
import { useTranslation } from '../context/LanguageContext';

// ChatWindow: solo la lista de mensajes. El formulario de entrada vive en
// App.tsx (componente <form className="composer">), fijo abajo del todo,
// para que la conversación se construya "hacia arriba" desde ahí — igual
// que en Claude. El scroll y el auto-scroll-to-bottom también los maneja
// App.tsx (necesita la ref del contenedor).
export default function ChatWindow({ messages, isLoading }) {
  const { t } = useTranslation();

  return (
    <div className="chat-window__log" role="log" aria-live="polite" aria-relevant="additions">
      {messages.map((msg) => (
        <div key={msg.id} className={`chat-message chat-message--${msg.role}`}>
          {msg.role === 'agent' && <NaviMascot size={32} className="chat-message__avatar" />}
          <div className="chat-message__body">
            <p className="chat-message__text">{msg.text}</p>
            {msg.rows?.length > 0 && (
              <div className="chat-message__rows">
                {msg.rows.map((row) => (
                  <BusRowCard key={`${row.stop_id}-${row.line_id}-${row.direction_id}`} row={row} />
                ))}
              </div>
            )}
          </div>
        </div>
      ))}

      {isLoading && (
        <div className="chat-message chat-message--agent">
          <NaviMascot size={32} className="chat-message__avatar" />
          <p className="chat-message__body chat-message--loading" aria-hidden="true">
            {t('loadingMessage')}
          </p>
        </div>
      )}
    </div>
  );
}
