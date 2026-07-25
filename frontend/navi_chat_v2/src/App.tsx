import { useState, useEffect, useCallback } from 'react';
import ChatContainer from '@/components/ChatContainer';
import MapPlaceholder from '@/components/MapPlaceholder';
import type { Lang } from '@/i18n/translations';
import type { FlyTarget } from '@/components/ChatContainer';
import { t } from '@/i18n/translations';

type View = 'chat' | 'map' | 'split';
type FontSize = 'normal' | 'large' | 'xlarge';

const languages: { code: Lang; label: string }[] = [
  { code: 'es', label: 'ES' },
  { code: 'en', label: 'EN' },
  { code: 'pt', label: 'PT' },
  { code: 'ko', label: 'KO' },
];

const fontSizes: { value: FontSize; label: string }[] = [
  { value: 'normal', label: 'A' },
  { value: 'large', label: 'A+' },
  { value: 'xlarge', label: 'A++' },
];

export default function App() {
  const [view, setView] = useState<View>('split');
  const [language, setLanguage] = useState<Lang>('es');
  const [highContrast, setHighContrast] = useState(false);
  const [fontSize, setFontSize] = useState<FontSize>('normal');
  const [flyTarget, setFlyTarget] = useState<FlyTarget | null>(null);

  useEffect(() => {
    document.documentElement.classList.toggle('high-contrast', highContrast);
  }, [highContrast]);

  useEffect(() => {
    document.documentElement.dataset.fontSize = fontSize;
  }, [fontSize]);

  useEffect(() => {
    const handler = (e: Event) => {
      const { view: v } = (e as CustomEvent).detail;
      setView(v);
    };
    window.addEventListener('nav:changeView', handler);
    return () => window.removeEventListener('nav:changeView', handler);
  }, []);

  const handleSetView = useCallback((v: View) => {
    setView(v);
    window.dispatchEvent(new Event('resize'));
  }, []);

  const handleQuickAction = useCallback((target: FlyTarget) => {
    setFlyTarget({ ...target });
  }, []);

  const tabs: { id: View; label: string }[] = [
    { id: 'chat', label: t(language, 'tabChat') },
    { id: 'map', label: t(language, 'tabMap') },
    { id: 'split', label: t(language, 'tabSplit') },
  ];

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden">
      <header
        className="flex h-16 shrink-0 items-center justify-between border-b border-[#d8d8d8] bg-white/90 backdrop-blur-md px-4 z-50 gap-2"
        style={{ fontFamily: 'var(--font-body)' }}
      >
        <div className="flex items-center gap-3 min-w-0">
          <img
            src="/icon-navi.svg"
            alt=""
            className="w-[38px] h-[38px] rounded-xl object-contain flex-shrink-0"
          />
          <div className="flex flex-col gap-0.5 min-w-0">
            <h1
              className="m-0 text-lg tracking-wider"
              style={{ fontFamily: 'var(--font-heading)' }}
            >
              NAVI
            </h1>
            <p className="m-0 text-xs text-[#555555] truncate max-w-[200px]">
              {t(language, 'tagline')}
            </p>
          </div>
        </div>

        <nav className="hidden md:flex gap-1 rounded-full border border-[#d8d8d8] p-0.5" role="tablist">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={view === tab.id}
              onClick={() => handleSetView(tab.id)}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors cursor-pointer ${
                view === tab.id
                  ? 'bg-[#0072B2] text-white'
                  : 'text-[#555555] hover:text-[#1a1a1a]'
              } ${tab.id === 'split' ? 'hidden lg:inline-block' : ''}`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setHighContrast((v) => !v)}
            className={`h-9 rounded-full border px-3 text-xs font-semibold cursor-pointer transition-colors ${
              highContrast
                ? 'bg-[#0072B2] text-white border-transparent'
                : 'bg-white text-[#1a1a1a] border-[#d8d8d8]'
            }`}
            title={t(language, 'themeLabel')}
          >
            ◐
          </button>

          <div className="flex rounded-full border border-[#d8d8d8] overflow-hidden">
            {fontSizes.map((fs) => (
              <button
                key={fs.value}
                type="button"
                onClick={() => setFontSize(fs.value)}
                className={`px-2.5 py-1.5 text-xs font-semibold cursor-pointer transition-colors ${
                  fontSize === fs.value
                    ? 'bg-[#0072B2] text-white'
                    : 'bg-white text-[#1a1a1a]'
                }`}
              >
                {fs.label}
              </button>
            ))}
          </div>

          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as Lang)}
            className="h-9 rounded-full border border-[#d8d8d8] bg-white px-3 text-xs font-bold text-[#1a1a1a] cursor-pointer outline-none"
            aria-label={t(language, 'langLabel')}
          >
            {languages.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <section
          className={`${
            view === 'map' ? 'hidden' : 'flex-1'
          } overflow-hidden`}
        >
          <ChatContainer language={language} onQuickAction={handleQuickAction} />
        </section>
        <section
          className={`${
            view === 'chat' ? 'hidden' : ''
          } flex-1 overflow-hidden ${view === 'split' ? 'hidden md:block' : ''}`}
        >
          <MapPlaceholder language={language} className="h-full w-full" flyTarget={flyTarget} />
        </section>
      </div>
    </div>
  );
}