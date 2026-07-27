import { useEffect, useCallback, useState } from 'react';
import ChatContainer from './components/ChatContainer'; // === NAVI-MAP: componente de tu compi (agente + mapa), sin cambios internos ===
import Map from './components/Map'; // === NAVI-MAP: sin tocar, ni una línea ===
import type { FlyTarget } from './components/ChatContainer'; // === NAVI-MAP ===
import type { Lang } from '@/i18n/translations'; // === NAVI-MAP: tipo que ya usaban ChatContainer/Map ===
import { t as tShared } from '@/i18n/translations'; // === FUSIÓN: t() de tu compi, renombrado para no chocar con tu t() de useTranslation() ===
import { AccessibilityProvider, useAccessibility } from './context/AccessibilityContext';
import { LanguageProvider, useTranslation } from './context/LanguageContext';
import { SUPPORTED_LANGUAGES } from './i18n/translations';
import './App.css';

// === NAVI-MAP: las 3 vistas posibles, igual que en la versión de tu compi ===
type View = 'chat' | 'map' | 'split';

function AppShell() {
  const { t, language, setLanguage } = useTranslation();
  const { theme, setTheme, fontSize, setFontSize } = useAccessibility();
  const [openSettings, setOpenSettings] = useState(false);

  // === NAVI-MAP: estado de vista/mapa (antes vivía en el App.tsx de tu
  // compi; ahora vive acá, junto con el resto del estado del shell). ===
  const [view, setView] = useState<View>('chat');
  const [isMapVisible, setIsMapVisible] = useState(false);
  const [flyTarget, setFlyTarget] = useState<FlyTarget | null>(null);

  // === NAVI-MAP: "puente" entre tu sistema de temas (atributo
  // data-theme, controlado por AccessibilityContext) y la clase
  // "high-contrast" que Map.tsx ya espera en <html> para invertir los
  // colores del mapa. No se tocó Map.tsx ni AccessibilityContext — esto
  // solo mantiene ambos sincronizados. ===
  useEffect(() => {
    document.documentElement.classList.toggle('high-contrast', theme === 'dark');
  }, [theme]);

  // === NAVI-MAP: igual que en el App.tsx de tu compi — permite que
  // ChatMessage/BusCard pidan cambiar de vista al hacer clic en "Ver en
  // el mapa". ===
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
    // Le da un frame a React para sacar la clase `hidden` del contenedor
    // del mapa antes de pedirle a MapLibre que recalcule tamaño.
    requestAnimationFrame(() => {
      window.dispatchEvent(new Event('resize'));
    });
  }, []);

  const handleQuickAction = useCallback((target: FlyTarget) => {
    setFlyTarget({ ...target });
  }, []);

  const handleFirstMessage = useCallback(() => {
    setIsMapVisible(true);
    setView('split');
  }, []);

  // === NAVI-MAP: visibilidad derivada del estado, no de display ligado
  // al breakpoint — así el chat y el mapa nunca se desmontan, solo se
  // ocultan con CSS (mismo criterio que usamos ayer para el fix de
  // móvil). ===
  const showChat = view !== 'map';
  const showMap = isMapVisible && view !== 'chat';
  const isSplit = showChat && showMap;
  const mapSolo = showMap && !showChat;

  const themeLabel = theme === 'dark' ? t('themeDark') : t('themeHighContrast');
  const fontLabel = fontSize === 'large' ? t('fontSizeLarge') : t('fontSizeNormal');

  // === FUSIÓN: ahora sí conectado a tabChat/tabMap/tabSplit del archivo
  // fusionado — ya sale traducido en es/en/pt/ko según el idioma activo. ===
  const viewTabs: { id: View; label: string }[] = [
    { id: 'chat', label: tShared(language as Lang, 'tabChat') },
    { id: 'map', label: tShared(language as Lang, 'tabMap') },
    { id: 'split', label: tShared(language as Lang, 'tabSplit') },
  ];

  return (
    <div className="app">
      {/* ============================================================
          Navbar: TAL CUAL la tenías. Único agregado: el <div className="view-switcher">
          dentro de .app__controls, marcado abajo con === NAVI-MAP ===.
          ============================================================ */}
      <header className="app__navbar">
        <div className="app__brand">
          <img src="/icon-navi.svg" alt="" className="app__brand-icon" />
          <div className="app__brand-text">
            <h1 className="app__brand-name">NAVI</h1>
            <p className="app__brand-tagline">{t('tagline')}</p>
          </div>

        </div>  


        <div className="app__controls">
          {/* === NAVI-MAP: selector Chat/Mapa/Ambos, versión escritorio.
              Solo aparece una vez que ya se mandó el primer mensaje
              (isMapVisible), igual que antes no había nada de mapa hasta
              ese momento. Se oculta en móvil vía CSS (ver App.css) y se
              reemplaza por la barra fija de abajo. === */}
          {isMapVisible && (
            <nav className="view-switcher" role="tablist" aria-label="Vista">
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

          {/* === NAVI-MAP: mismo selector, versión dentro del modal de
              ajustes de móvil (<=480px), para no perderlo cuando
              .app__controls se oculta del todo. === */}
          {isMapVisible && (
            <nav className="view-switcher" role="tablist" aria-label="Vista">
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

      {/* ============================================================
          === NAVI-MAP: .app__body reemplaza lo que antes era
          .app__panel como hijo directo de .app. Ahora .app__panel y
          .app__map-panel son dos tarjetas hermanas dentro de
          .app__body. Ninguna de las dos se desmonta nunca — se ocultan
          con clases CSS (--hidden) para no perder el historial del chat
          ni reinicializar MapLibre.
          ============================================================ */}
      <div className="app__body">
        <div className={`app__panel ${isSplit ? 'app__panel--split' : ''} ${!showChat ? 'app__panel--hidden' : ''}`}>
          {/* ChatContainer trae SU PROPIO <main id="main-content" className="app__main">
              por dentro (reskin de las clases de tu compi a las tuyas),
              así que acá no hace falta envolverlo de nuevo. */}
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

      {/* === NAVI-MAP: selector de vista fijo abajo, solo visible en
          móvil (ver media query en App.css) y solo una vez que hay
          mapa disponible. === */}
      {isMapVisible && (
        <nav className="view-switcher view-switcher--mobile" role="tablist" aria-label="Vista">
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
