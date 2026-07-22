import { useState, useRef } from 'react';
import { askNaviAgent } from '../services/naviAgent';
import BusRowCard from './BusRowCard';

export default function ChatWindow() {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'agent',
      text: 'Hola, soy Navi 🚌 Pregúntame por cualquier línea o parada cerca de Puerta del Sol.',
      rows: [],
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef(null);

  async function handleSubmit(event) {
    event.preventDefault();
    const question = input.trim();
    if (!question || isLoading) return;

    const userMessage = { id: crypto.randomUUID(), role: 'user', text: question, rows: [] };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const { answerText, rows } = await askNaviAgent(question);
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'agent', text: answerText, rows },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'agent',
          text: 'No pude consultar los datos en este momento. Intenta de nuevo en unos segundos.',
          rows: [],
        },
      ]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }

  return (
    <section className="chat-window" aria-label="Conversación con Navi">
      {/*
        aria-live="polite": el lector de pantalla anuncia cada respuesta nueva
        del agente sin interrumpir lo que el usuario esté haciendo/leyendo.
        NO usar "assertive" aquí: cortaría al usuario a mitad de frase cada
        vez que llega una respuesta, lo cual es agresivo para este caso de uso.
      */}
      <div className="chat-window__log" role="log" aria-live="polite" aria-relevant="additions">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`chat-message chat-message--${msg.role}`}
          >
            <p className="chat-message__text">{msg.text}</p>
            {msg.rows.length > 0 && (
              <div className="chat-message__rows">
                {msg.rows.map((row) => (
                  <BusRowCard key={`${row.stop_id}-${row.line_id}-${row.direction_id}`} row={row} />
                ))}
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <p className="chat-message chat-message--agent chat-message--loading" aria-hidden="true">
            Navi está consultando…
          </p>
        )}
      </div>

      <form onSubmit={handleSubmit} className="chat-window__form">
        <label htmlFor="navi-question" className="visually-hidden">
          Escribe tu pregunta sobre buses
        </label>
        <input
          id="navi-question"
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ej: ¿cuánto tarda la línea 27?"
          autoComplete="off"
        />
        <button type="submit" disabled={isLoading || !input.trim()}>
          Preguntar
        </button>
      </form>
    </section>
  );
}
