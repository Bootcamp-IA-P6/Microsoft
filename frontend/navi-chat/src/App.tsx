import { useRef, useState } from 'react';
import ChatWindow from './components/ChatWindow';
import NaviMascot from './components/NaviMascot';
import VoiceInputButton from './components/VoiceInputButton';
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

  function handleSubmit(event) {
    event.preventDefault();
    sendQuestion(input.trim());
  }

  function handleVoiceResult(transcript) {
    sendQuestion(transcript.trim());
  }

  const quickActions = [
    { label: t('quickActionNextBus'), prompt: t('quickActionPromptNextBus') },
    { label: t('quickActionHowReach'), prompt: t('quickActionPromptHowReach') },
    { label: t('quickActionRoadworks'), prompt: t('quickActionPromptRoadworks') },
  ];

  return (
    <div className="app">
      <div className="app__panel">
        <a href="#main-content" className="skip-link">
          {t('skipLink')}
        </a>

        <header className="app__topbar">
          <div className="app__brand-text">
            <h1 className="app__brand-name">NAVI</h1>
            <p className="app__brand-tagline">{t('tagline')}</p>
          </div>

          <div className="app__controls">
            <div className="switch-control">
              <span className="switch-control__label">{t('settingsAppearance')}</span>
              <div className="toggle-with-labels">
                <span className="toggle-label toggle-label--off">{t('themeDark')}</span>
                <label className="toggle" aria-label={themeLabel} title={themeLabel}>
                  <input
                    type="checkbox"
                    checked={theme === 'high-contrast'}
                    onChange={() => setTheme(theme === 'dark' ? 'high-contrast' : 'dark')}
                  />
                  <span className="toggle__track" />
                  <span className="toggle__thumb" />
                </label>
                <span className="toggle-label toggle-label--on">{t('themeHighContrast')}</span>
              </div>
            </div>

            <div className="switch-control">
              <span className="switch-control__label">{t('settingsFontSize')}</span>
              <div className="toggle-with-labels">
                <span className="toggle-label toggle-label--off">{t('fontSizeNormal')}</span>
                <label className="toggle" aria-label={fontLabel} title={fontLabel}>
                  <input
                    type="checkbox"
                    checked={fontSize === 'large'}
                    onChange={() => setFontSize(fontSize === 'normal' ? 'large' : 'normal')}
                  />
                  <span className="toggle__track" />
                  <span className="toggle__thumb" />
                </label>
                <span className="toggle-label toggle-label--on">{t('fontSizeLarge')}</span>
              </div>
            </div>

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
        </header>

        <main id="main-content">
          <section className="hero">
            <NaviMascot size={96} />
            <div className="hero__copy">
              <h2>{t('heroTitle')}</h2>
              <p>{t('heroSubtitle')}</p>
            </div>

            <form className="hero__query" onSubmit={handleSubmit}>
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
              <button type="submit" className="hero__submit" disabled={isLoading || !input.trim()}>
                {t('askButton')}
              </button>
            </form>

            <div className="hero__quick-actions">
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
          </section>

          <ChatWindow messages={messages} isLoading={isLoading} />
        </main>

        <footer className="app__footer">
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
