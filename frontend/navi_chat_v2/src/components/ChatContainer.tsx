import { useState, useRef, useEffect, useCallback } from 'react';
import ChatMessage from './ChatMessage';
import { askAgent } from '@/services/agentService';
import type { ChatResponse } from '@/services/agentService';
import { extractAllStops } from '@/services/parseStops';
import type { Lang } from '@/i18n/translations';
import { t, speechLang } from '@/i18n/translations';

interface Message {
  id: string;
  role: 'user' | 'agent';
  text: string;
  matchedStops?: string[];
}

export interface FlyTarget {
  lng: number;
  lat: number;
  zoom: number;
}

interface ChatContainerProps {
  language: Lang;
  onQuickAction?: (target: FlyTarget) => void;
}

const QUICK_ACTION_TARGETS: FlyTarget[] = [
  { lng: -3.7008, lat: 40.4088, zoom: 15 },
  { lng: -3.6892, lat: 40.4669, zoom: 15 },
  { lng: -3.7038, lat: 40.4168, zoom: 13 },
];

export default function ChatContainer({ language, onQuickAction }: ChatContainerProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

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

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      text: question,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const { answerText }: ChatResponse = await askAgent(question, language);
      const matchedStops = extractAllStops(answerText, question);

      const agentMsg: Message = {
        id: crypto.randomUUID(),
        role: 'agent',
        text: answerText,
        matchedStops,
      };
      setMessages((prev) => [...prev, agentMsg]);
    } catch {
      const errorMsg: Message = {
        id: crypto.randomUUID(),
        role: 'agent',
        text: t(language, 'error'),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }

  const hasMessages = messages.length > 0 || isLoading;

  const quickActions = [
    { label: t(language, 'quickNextBus'), prompt: t(language, 'quickNextBusPrompt') },
    { label: t(language, 'quickHowReach'), prompt: t(language, 'quickHowReachPrompt') },
    { label: t(language, 'quickDelays'), prompt: t(language, 'quickDelaysPrompt') },
  ];

  return (
    <div className="flex h-full flex-col bg-white/92 p-5 overflow-hidden" style={{ backdropFilter: 'blur(10px)' }}>
      <div className="flex-1 min-h-0 overflow-y-auto px-1 py-2 pb-6">
        {!hasMessages ? (
          <div className="flex h-full flex-col items-center justify-center text-center gap-5 px-5">
            <span className="w-24 h-24 rounded-full overflow-hidden flex items-center justify-center bg-[#eef6f3]">
              <img
                src="/navi-mascot.svg"
                alt=""
                className="w-full h-full object-cover"
                onError={(e) => {
                  (e.currentTarget as HTMLImageElement).style.display = 'none';
                }}
              />
            </span>
            <div>
              <h2 className="m-0 text-2xl font-bold" style={{ fontFamily: 'var(--font-heading)' }}>
                {t(language, 'greeting')}
              </h2>
              <p className="m-1 mt-1 text-sm text-[#555555]">
                {t(language, 'subtitle')}
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              {quickActions.map((action, i) => (
                <button
                  key={action.prompt}
                  type="button"
                  onClick={() => {
                    onQuickAction?.(QUICK_ACTION_TARGETS[i]);
                    handleSend(action.prompt);
                  }}
                  disabled={isLoading}
                  className="rounded-full border border-[#d8d8d8] bg-white px-4 py-2 text-sm text-[#1a1a1a] cursor-pointer transition-transform hover:-translate-y-0.5 disabled:opacity-50"
                >
                  {action.label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-3" role="log" aria-live="polite" aria-relevant="additions">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} role={msg.role} text={msg.text} matchedStops={msg.matchedStops} />
            ))}
            {isLoading && (
              <div className="flex items-center gap-2 text-sm text-[#555555] italic self-start pl-10">
                <span className="animate-pulse">●</span>
                <span className="animate-pulse delay-150">●</span>
                <span className="animate-pulse delay-300">●</span>
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
        className="flex shrink-0 items-center gap-2 rounded-full border border-[#d8d8d8] bg-white px-4 py-2 mt-3"
      >
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t(language, 'inputPlaceholder')}
          className="flex-1 min-w-0 border-none bg-transparent text-sm outline-none text-[#1a1a1a]"
          disabled={isLoading}
          autoComplete="off"
        />
        {recognitionRef.current !== null && (
          <button
            type="button"
            onClick={handleVoiceToggle}
            disabled={isLoading}
            className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 cursor-pointer transition-colors ${
              isListening
                ? 'bg-[#D55E00] text-white'
                : 'bg-transparent text-[#555555] border border-[#d8d8d8]'
            }`}
            aria-label="Voice input"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="22" />
            </svg>
          </button>
        )}
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="w-11 h-11 rounded-full bg-[#0072B2] text-white flex items-center justify-center shrink-0 cursor-pointer disabled:bg-[#b8b8b8] disabled:cursor-not-allowed"
          aria-label={t(language, 'send')}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </form>
    </div>
  );
}