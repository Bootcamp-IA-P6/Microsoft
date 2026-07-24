import { useEffect, useRef, useState } from 'react';
import ChatWindow from './components/ChatWindow';
import NaviMascot from './components/NaviMascot';
import VoiceInputButton, { SendIcon } from './components/VoiceInputButton';
import { AccessibilityProvider, useAccessibility } from './context/AccessibilityContext';
import { LanguageProvider, useTranslation } from './context/LanguageContext';
import { SUPPORTED_LANGUAGES } from './i18n/translations';
import { askNaviAgent } from './services/naviAgent';
import './App.css';

type ChatMessage = {
  id: string;
  role: 'user' | 'agent';
  text: string;
  rows: any[];
};

function AppShell() {
  const { t, language, setLanguage } = useTranslation();
  const { theme, setTheme, fontSize, setFontSize } = useAccessibility();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const conversationRef = useRef<HTMLDivElement | null>(null);
  const [openSettings, setOpenSettings] = useState(false);

  useEffect(() => {
    const el = conversationRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, isLoading]);

  const themeLabel = theme === 'dark' ? t('themeDark') : t('themeHighContrast');
  const fontLabel = fontSize === 'large' ? t('fontSizeLarge') : t('fontSizeNormal');

  async function sendQuestion(question: string) {
    if (!question || isLoading) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      text: question,
      rows: [],
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const { answerText, rows } = await askNaviAgent(question, language);
      const agentMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'agent',
        text: answerText,
        rows,
      };
      setMessages((prev) => [...prev, agentMessage]);
    } catch {
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'agent',
        text: t('errorMessage'),
        rows: [],
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    sendQuestion(input.trim());
  }

  function handleVoiceResult(transcript: string) {
    sendQuestion(transcript.trim());
  }

  const quickActions = [
    { label: t('quickActionNextBus'), prompt: t('quickActionPromptNextBus') },
    { label: t('quickActionHowReach'), prompt: t('quickActionPromptHowReach') },
    { label: t('quickActionRoadworks'), prompt: t('quickActionPromptRoadworks') },
  ];

  const hasMessages = messages.length > 0 || isLoading;

  return (
    <div className="app">
      {/* Navbar: ahora es un hermano de .app__panel, no vive adentro —
          ancho completo, fija arriba, independiente de si el chat crece. */}
      <header className="app__navbar">
        <div className="app__brand">
          <img src="/icon-navi.svg" alt="" className="app__brand-icon" />
          <div className="app__brand-text">
            <h1 className="app__brand-name">NAVI</h1>
            <p className="app__brand-tagline">{t('tagline')}</p>
          </div>

        </div>  


        <div className="app__controls">
          <button
            type="button"
            className="pill-toggle"
            aria-pressed={theme === 'high-contrast'}
            onClick={() => setTheme(theme === 'dark' ? 'high-contrast' : 'dark')}
            title={themeLabel}
          >
            <span aria-hidden="true">{theme === 'high-contrast' ? '◐' : '🌙'}</span>
            <span className="pill-toggle__label">{themeLabel}</span>
          </button>

      
          <button
            type="button"
            className="pill-toggle"
            aria-pressed={fontSize === 'large'}
            onClick={() => setFontSize(fontSize === 'normal' ? 'large' : 'normal')}
            title={fontLabel}
          >
            <span aria-hidden="true" className="pill-toggle__aa">Aa</span>
            <span className="pill-toggle__label">{fontLabel}</span>
          </button>

          <label className="language-select" aria-label={t('settingsLanguage')}>
            <select value={language} onChange={(e) => setLanguage(e.target.value)}>
              {SUPPORTED_LANGUAGES.map((option) => (
                <option key={option.code} value={option.code}>
                  {option.code.toUpperCase()}
                </option>
              ))}
            </select>
          </label>
        </div>

      {openSettings && (
        <div className="settings-modal">
          <button
            type="button"
            className="pill-toggle"
            onClick={() => setTheme(theme === 'dark' ? 'high-contrast' : 'dark')}
          >
            {themeLabel}
          </button>

          <button
            type="button"
            className="pill-toggle"
            onClick={() => setFontSize(fontSize === 'normal' ? 'large' : 'normal')}
          >
            {fontLabel}
          </button>

          <label className="language-select" aria-label={t('settingsLanguage')}>
            <select value={language} onChange={(e) => setLanguage(e.target.value)}>
              {SUPPORTED_LANGUAGES.map((option) => (
                <option key={option.code} value={option.code}>
                  {option.code.toUpperCase()}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      <button
        className="mobile-settings"
        onClick={() => setOpenSettings((prev) => !prev)}
        aria-expanded={openSettings}
        aria-label={t('settings')}
      >
        ⚙️
      </button>
      </header>

      <a href="#main-content" className="skip-link">
        {t('skipLink')}
      </a>

      <div className="app__panel">
        <main id="main-content" className="app__main">
          <div className="conversation-area" ref={conversationRef}>
            {!hasMessages ? (
              <div className="empty-state">
                <NaviMascot size={96} />
                <div className="empty-state__copy">
                  <h2>{t('heroTitle')}</h2>
                  <p>{t('heroSubtitle')}</p>
                </div>
                <div className="empty-state__quick-actions">
                  {quickActions.map((action) => (
                    <button
                      key={action.prompt}
                      type="button"
                      className="action-chip"
                      onClick={() => sendQuestion(action.prompt)}
                      disabled={isLoading}
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <ChatWindow messages={messages} isLoading={isLoading} />
            )}
          </div>

          <form className="composer" onSubmit={handleSubmit}>
            <label htmlFor="navi-question" className="visually-hidden">
              {t('inputLabel')}
            </label>
            <input
              id="navi-question"
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t('inputPlaceholder')}
              autoComplete="off"
            />
            <VoiceInputButton onResult={handleVoiceResult} disabled={isLoading} />
            <button
              type="submit"
              className="composer__submit"
              disabled={isLoading || !input.trim()}
              aria-label={t('askButton')}
              title={t('askButton')}
            >
              <SendIcon />
            </button>
          </form>
        </main>

        <footer className="app__footer">
          <span aria-hidden="true" className="app__footer-icon">i</span>
          <p>{t('footerNote')}</p>
        </footer>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AccessibilityProvider>
      <LanguageProvider>
        <AppShell />
      </LanguageProvider>
    </AccessibilityProvider>
  );
}
