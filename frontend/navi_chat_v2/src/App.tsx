import { useEffect, useCallback, useState } from 'react';
import ChatContainer from './components/ChatContainer';
import Map from './components/Map';
import type { FlyTarget } from './components/ChatContainer';
import type { Lang } from '@/i18n/translations';
import { t as tShared } from '@/i18n/translations';
import { AccessibilityProvider, useAccessibility } from './context/AccessibilityContext';
import { LanguageProvider, useTranslation } from './context/LanguageContext';
import { SUPPORTED_LANGUAGES } from './i18n/translations';
import './App.css';

type View = 'chat' | 'map' | 'split';

function AppShell() {
  const { t, language, setLanguage } = useTranslation();
  const { theme, setTheme, fontSize, setFontSize } = useAccessibility();
  const [openSettings, setOpenSettings] = useState(false);

  const [view, setView] = useState<View>('chat');
  const [isMapVisible, setIsMapVisible] = useState(false);
  const [flyTarget, setFlyTarget] = useState<FlyTarget | null>(null);

  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 768px)');
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle('high-contrast', theme === 'dark');
  }, [theme]);

  useEffect(() => {
    const handler = (e: Event) => {
      const { view: v } = (e as CustomEvent).detail;
      setView(v as View);
    };
    window.addEventListener('nav:changeView', handler);
    return () => window.removeEventListener('nav:changeView', handler);
  }, []);

  const handleSetView = useCallback((v: View) => {
    setView(v);
    requestAnimationFrame(() => {
      window.dispatchEvent(new Event('resize'));
    });
  }, []);

  const handleQuickAction = useCallback((target: FlyTarget) => {
    setFlyTarget({ ...target });
  }, []);

  const handleFirstMessage = useCallback(() => {
    setIsMapVisible(true);
    setView(isMobile ? 'map' : 'split');
  }, [isMobile]);

  const showChat = view !== 'map';
  const showMap = isMapVisible && view !== 'chat';
  const isSplit = showChat && showMap;
  const mapSolo = showMap && !showChat;

  const viewTabs: { id: View; label: string }[] = [
    { id: 'chat', label: tShared(language as Lang, 'tabChat') },
    { id: 'map', label: tShared(language as Lang, 'tabMap') },
    { id: 'split', label: tShared(language as Lang, 'tabSplit') },
  ];

  const mobileViewTabs = viewTabs.filter((tab) => tab.id !== 'split');

  return (
    <div className="app">
      <header className="app__navbar">
        <div className="app__brand">
          <img src="/icon-navi.svg" alt="" className="app__brand-icon" />
          <div className="app__brand-text">
            <h1 className="app__brand-name">NAVI</h1>
            <p className="app__brand-tagline">{t('tagline')}</p>
          </div>
        </div>

        {isMapVisible && (
          <nav className="view-switcher view-switcher--desktop" role="tablist" aria-label="Vista">
            {viewTabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={view === tab.id}
                className="view-switcher__btn"
                onClick={() => handleSetView(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        )}

        <div className="app__controls">
          <button
            type="button"
            className="app__settings-btn"
            onClick={() => setOpenSettings((prev) => !prev)}
            aria-expanded={openSettings}
            aria-label={t('settings')}
          >
            {isMobile ? (
              <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
                <circle cx="12" cy="5" r="2" />
                <circle cx="12" cy="12" r="2" />
                <circle cx="12" cy="19" r="2" />
              </svg>
            ) : (
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3" />
                <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
              </svg>
            )}
          </button>
        </div>
      </header>

      {openSettings && (
        <div className="settings-panel">
          <div className="settings-panel__backdrop" onClick={() => setOpenSettings(false)} />
          <div className={`settings-panel__content ${isMobile ? 'settings-panel__content--mobile' : ''}`}>
            <h3 className="settings-panel__title">{t('settings')}</h3>

            <label className="settings-panel__label">{t('settingsTheme')}</label>
            <div className="settings-panel__row settings-panel__row--split">
              <button
                type="button"
                className={`settings-panel__half settings-panel__contrast-btn ${theme !== 'high-contrast' ? 'settings-panel__contrast-btn--active' : ''}`}
                onClick={() => setTheme('dark')}
              >
                <span>{t('themeNormal')}</span>
              </button>
              <button
                type="button"
                className={`settings-panel__half settings-panel__contrast-btn ${theme === 'high-contrast' ? 'settings-panel__contrast-btn--active' : ''}`}
                onClick={() => setTheme('high-contrast')}
              >
                <span>{t('themeHighContrast')}</span>
              </button>
            </div>

            <label className="settings-panel__label">{t('settingsFontSize')}</label>
            <div className="settings-panel__row settings-panel__row--split">
              <button
                type="button"
                className="pill-toggle settings-panel__half"
                onClick={() => setFontSize(fontSize === 'large' ? 'normal' : fontSize === 'xlarge' ? 'large' : 'normal')}
                disabled={fontSize === 'normal'}
              >
                <span aria-hidden="true" className="pill-toggle__aa">A–</span>
              </button>
              <button
                type="button"
                className="pill-toggle settings-panel__half"
                onClick={() => setFontSize(fontSize === 'normal' ? 'large' : fontSize === 'large' ? 'xlarge' : 'xlarge')}
                disabled={fontSize === 'xlarge'}
              >
                <span aria-hidden="true" className="pill-toggle__aa">A+</span>
              </button>
            </div>

            <label className="settings-panel__label">{t('settingsLanguage')}</label>
            <label className="language-select settings-panel__select">
              <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                {SUPPORTED_LANGUAGES.map((option) => (
                  <option key={option.code} value={option.code}>
                    {option.code.toUpperCase()}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
      )}

      <a href="#main-content" className="skip-link">
        {t('skipLink')}
      </a>

      <div className="app__body">
        <div className={`app__panel ${isSplit ? 'app__panel--split' : ''} ${!showChat ? 'app__panel--hidden' : ''}`}>
          <ChatContainer
            language={language as Lang}
            onQuickAction={handleQuickAction}
            onFirstMessage={handleFirstMessage}
          />

          <footer className="app__footer">
            <span aria-hidden="true" className="app__footer-icon">i</span>
            <p>{t('footerNote')}</p>
          </footer>
        </div>

        <div
          className={`app__map-panel ${mapSolo ? 'app__map-panel--solo' : ''} ${!showMap ? 'app__map-panel--hidden' : ''}`}
        >
          <Map language={language as Lang} className="app__map-fill" flyTarget={flyTarget} isMapVisible={isMapVisible} />
        </div>
      </div>

      {isMapVisible && (
        <nav className="view-switcher view-switcher--mobile" role="tablist" aria-label="Vista">
          {mobileViewTabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={view === tab.id}
              className="view-switcher__btn"
              onClick={() => handleSetView(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      )}
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
