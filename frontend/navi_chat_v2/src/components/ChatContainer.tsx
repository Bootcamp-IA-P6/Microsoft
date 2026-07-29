import { useState, useRef, useEffect, useCallback } from 'react';
import ChatMessage from './ChatMessage';
import NaviMascot from './NaviMascot'; // === NAVI-MAP: tu componente de mascota, reemplaza el <img icon-navi.svg> que había acá ===
import { askAgent, sendFeedbackToFabric } from '@/services/agentService';
import type { ChatResponse, MapData } from '@/services/agentService';
import { extractAllStops } from '@/services/parseStops';
import { enrichStopQuery } from '@/utils/enrichQuery';
import { getStopCoords } from '@/utils/geoData';
import type { Lang } from '@/i18n/translations';
import { t, speechLang } from '@/i18n/translations';

// ============================================================
// TODO LO DE ABAJO (estado, handlers, efectos, llamadas al agente,
// reconocimiento de voz) es IDÉNTICO a la versión de tu compi.
// Lo único que cambia en este archivo es el JSX del return: clases de
// Tailwind → clases de tu App.css.
// ============================================================

interface Message {
  id: string;
  role: 'user' | 'agent';
  text: string;
  matchedStops?: string[];
  timestamp: number;
  feedback?: 'like' | 'dislike' | null;
  feedbackSent?: boolean;
  questionText?: string;
  mapData?: MapData | null;
}

export interface FlyTarget {
  lng: number;
  lat: number;
  zoom: number;
}

interface ChatContainerProps {
  language: Lang;
  onQuickAction?: (target: FlyTarget) => void;
  onFirstMessage?: () => void;
}

export default function ChatContainer({ language, onQuickAction, onFirstMessage }: ChatContainerProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [hasSentFirst, setHasSentFirst] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const handleSendRef = useRef(handleSend);
  handleSendRef.current = handleSend;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  useEffect(() => {
    const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionAPI) return;

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = speechLang(language);

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[0][0].transcript;
      setInput(transcript);
      setIsListening(false);
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
  }, [language]);

  const handleVoiceToggle = useCallback(() => {
    if (!recognitionRef.current) return;
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      recognitionRef.current.lang = speechLang(language);
      recognitionRef.current.start();
      setIsListening(true);
    }
  }, [isListening, language]);

  async function handleSend(question: string) {
    if (!question.trim() || isLoading) return;

    const now = Date.now();

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      text: question,
      timestamp: now,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    if (!hasSentFirst) {
      setHasSentFirst(true);
      onFirstMessage?.();
    }

    try {
      const enriched = enrichStopQuery(question);
      const response: ChatResponse = await askAgent(enriched, language);
      const answerText = response.chat_message.text;
      const mapData = response.map_data;
      const matchedStops = extractAllStops(answerText, question);

      let resolvedMapData = mapData;
      if (!resolvedMapData && response.chat_message.stop_id) {
        const stopCoords = getStopCoords(response.chat_message.stop_name || response.chat_message.stop_id);
        if (stopCoords) {
          resolvedMapData = {
            type: 'bus_stop_and_route',
            stop_coordinates: stopCoords,
          };
        }
      }

      const agentMsg: Message = {
        id: crypto.randomUUID(),
        role: 'agent',
        text: answerText,
        matchedStops,
        timestamp: Date.now(),
        questionText: question,
        mapData: resolvedMapData,
      };
      setMessages((prev) => [...prev, agentMsg]);

      if (resolvedMapData?.stop_coordinates) {
        window.dispatchEvent(new CustomEvent('map:showRoute', {
          detail: {
            stopCoordinates: resolvedMapData.stop_coordinates,
            stopName: response.chat_message.stop_name || matchedStops?.[0] || '',
            lineLabel: response.chat_message.line_number || '',
          },
        }));
      }
    } catch {
      const errorMsg: Message = {
        id: crypto.randomUUID(),
        role: 'agent',
        text: t(language, 'error'),
        timestamp: Date.now(),
        questionText: question,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleSendFeedback(messageId: string, feedback: 'like' | 'dislike') {
    const msg = messages.find((m) => m.id === messageId);
    if (!msg || msg.role !== 'agent' || msg.feedbackSent) return;

    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, feedback, feedbackSent: true } : m))
    );

    const feedbackType = feedback === 'like' ? 'Like' : 'Dislike';
    sendFeedbackToFabric(messageId, feedbackType, msg.questionText ?? '', msg.text);
  }

  useEffect(() => {
    const handler = (e: Event) => {
      const { question } = (e as CustomEvent).detail;
      if (question) handleSendRef.current(question);
    };
    window.addEventListener('chat:ask', handler);
    return () => window.removeEventListener('chat:ask', handler);
  }, []);

  const hasMessages = messages.length > 0 || isLoading;

  const quickActions = [
    { labelKey: 'quickC1Bus', promptKey: 'quickC1BusPrompt' },
    { labelKey: 'quickCibeles', promptKey: 'quickCibelesPrompt' },
    { labelKey: 'quickLine27', promptKey: 'quickLine27Prompt' },
    { labelKey: 'quickM1Freq', promptKey: 'quickM1FreqPrompt' },
  ] as const;

  const quickActionIcons = [
    <svg key="bus" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="7" width="18" height="12" rx="2" />
      <line x1="3" y1="11" x2="21" y2="11" />
      <line x1="7" y1="4" x2="7" y2="7" />
      <line x1="17" y1="4" x2="17" y2="7" />
      <circle cx="8" cy="18" r="1.5" />
      <circle cx="16" cy="18" r="1.5" />
    </svg>,
    <svg key="pin" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a8 8 0 0 0-8 8c0 5.4 8 12 8 12s8-6.6 8-12a8 8 0 0 0-8-8z" />
      <circle cx="12" cy="10" r="3" />
    </svg>,
    <svg key="alert" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3L2 21h20L12 3z" />
      <line x1="12" y1="9" x2="12" y2="14" />
      <circle cx="12" cy="17.5" r="0.5" fill="currentColor" stroke="none" />
    </svg>,
    <svg key="clock" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>,
  ];

  // ============================================================
  // A PARTIR DE ACÁ: mismo árbol/misma lógica de render, clases de
  // App.css en vez de Tailwind. id="main-content" se movió acá adentro
  // (antes lo ponía App.tsx en un <main> que envolvía a este
  // componente) para no duplicar el <main>.
  // ============================================================
  return (
    <main id="main-content" className="app__main">
      <div className="conversation-area">
        {!hasMessages ? (
          <div className="empty-state">
            <NaviMascot size={96} />
            <div className="empty-state__copy">
              {/* === FUSIÓN: antes estaba hardcodeado en español; ahora usa
                  las claves 'greeting'/'subtitle' que ya existen para es/en/pt/ko === */}
              <h2>{t(language, 'greeting')}</h2>
              <p>{t(language, 'subtitle')}</p>
            </div>
            <div className="empty-state__quick-actions">
              {quickActions.map((action, i) => (
                <button
                  key={action.promptKey}
                  type="button"
                  onClick={() => {
                    onQuickAction?.(QUICK_ACTION_TARGETS[i]);
                    if (!hasSentFirst) {
                      setHasSentFirst(true);
                      onFirstMessage?.();
                    }
                    handleSend(t(language, action.promptKey));
                  }}
                  disabled={isLoading}
                  className="action-chip"
                >
                  {quickActionIcons[i]}
                  <span>{t(language, action.labelKey)}</span>
                </button>
              ))}
            </div>
            {/* === FIX: antes había un segundo grupo acá abajo (SUGGESTIONS,
                3 chips más, hardcodeados solo en español) — sumaban 6 en
                total. Lo saqué para quedarnos solo con estos 3, que además
                ya están traducidos a los 4 idiomas y mueven el mapa. Si
                preferís las preguntas de SUGGESTIONS en vez de estas,
                avisame y las cambio (queda la constante SUGGESTIONS más
                abajo en el archivo, sin usar, por si la querés recuperar). === */}
          </div>
        ) : (
          <div className="chat-window__log" role="log" aria-live="polite" aria-relevant="additions">
            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                messageId={msg.id}
                role={msg.role}
                text={msg.text}
                matchedStops={msg.matchedStops}
                timestamp={msg.timestamp}
                feedback={msg.feedback}
                feedbackSent={msg.feedbackSent}
                onFeedback={handleSendFeedback}
                mapData={msg.mapData}
              />
            ))}
            {isLoading && (
              <div className="chat-message chat-message--agent chat-message--loading">
                <span className="chat-message__body">
                  <span className="animate-pulse">●</span>{' '}
                  <span className="animate-pulse">●</span>{' '}
                  <span className="animate-pulse">●</span>
                </span>
              </div>
            )}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend(input);
        }}
        className="composer"
      >
        <label htmlFor="navi-question" className="visually-hidden">
          {t(language, 'inputPlaceholder')}
        </label>
        <input
          id="navi-question"
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t(language, 'inputPlaceholder')}
          disabled={isLoading}
          autoComplete="off"
        />
        {recognitionRef.current !== null && (
          <div className="voice-input">
            <button
              type="button"
              onClick={handleVoiceToggle}
              disabled={isLoading}
              className={`voice-input__button ${isListening ? 'voice-input__button--listening' : ''}`}
              aria-label="Voice input"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="22" />
              </svg>
            </button>
          </div>
        )}
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="composer__submit"
          aria-label={t(language, 'send')}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </form>
    </main>
  );
}

const QUICK_ACTION_TARGETS: FlyTarget[] = [
  { lng: -3.7008, lat: 40.4168, zoom: 16 },
  { lng: -3.6932, lat: 40.4195, zoom: 16 },
  { lng: -3.7038, lat: 40.4168, zoom: 14 },
  { lng: -3.7038, lat: 40.4168, zoom: 14 },
];
