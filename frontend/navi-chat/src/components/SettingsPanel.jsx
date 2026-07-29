import { useRef, useState, useEffect } from 'react';
import { useAccessibility } from '../context/AccessibilityContext';
import { useTranslation } from '../context/LanguageContext';
import { SUPPORTED_LANGUAGES } from '../i18n/translations';

// SettingsPanel: un botón que abre un panel con 3 grupos de radio buttons
// (tema, tamaño de letra, idioma). Radios nativos a propósito — navegables
// por teclado y leídos por lectores de pantalla sin trabajo extra.

export default function SettingsPanel() {
  const { theme, setTheme, fontSize, setFontSize } = useAccessibility();
  const { t, language, setLanguage } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const panelRef = useRef(null);
  const buttonRef = useRef(null);

  const THEME_OPTIONS = [
    { value: 'light', label: t('themeLight') },
    { value: 'dark', label: t('themeDark') },
    { value: 'high-contrast', label: t('themeHighContrast') },
  ];
  const FONT_SIZE_OPTIONS = [
    { value: 'normal', label: t('fontSizeNormal') },
    { value: 'large', label: t('fontSizeLarge') },
    { value: 'xlarge', label: t('fontSizeXLarge') },
  ];

  useEffect(() => {
    if (!isOpen) return;
    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        setIsOpen(false);
        buttonRef.current?.focus();
      }
    }
    function handleClickOutside(e) {
      if (panelRef.current && !panelRef.current.contains(e.target) && !buttonRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  return (
    <div className="settings">
      <button
        ref={buttonRef}
        type="button"
        className="settings__trigger"
        aria-expanded={isOpen}
        aria-controls="settings-panel"
        onClick={() => setIsOpen((v) => !v)}
      >
        <span aria-hidden="true">⚙</span>
        <span className="visually-hidden">{t('settingsTrigger')}</span>
      </button>

      {isOpen && (
        <div id="settings-panel" ref={panelRef} className="settings__panel" role="dialog" aria-label={t('settingsTrigger')}>
          <fieldset className="settings__group">
            <legend>{t('settingsAppearance')}</legend>
            {THEME_OPTIONS.map((opt) => (
              <label key={opt.value} className="settings__option">
                <input
                  type="radio"
                  name="theme"
                  value={opt.value}
                  checked={theme === opt.value}
                  onChange={() => setTheme(opt.value)}
                />
                {opt.label}
              </label>
            ))}
          </fieldset>

          <fieldset className="settings__group">
            <legend>{t('settingsFontSize')}</legend>
            {FONT_SIZE_OPTIONS.map((opt) => (
              <label key={opt.value} className="settings__option">
                <input
                  type="radio"
                  name="fontSize"
                  value={opt.value}
                  checked={fontSize === opt.value}
                  onChange={() => setFontSize(opt.value)}
                />
                {opt.label}
              </label>
            ))}
          </fieldset>

          <fieldset className="settings__group">
            <legend>{t('settingsLanguage')}</legend>
            {SUPPORTED_LANGUAGES.map((opt) => (
              <label key={opt.code} className="settings__option">
                <input
                  type="radio"
                  name="language"
                  value={opt.code}
                  checked={language === opt.code}
                  onChange={() => setLanguage(opt.code)}
                />
                {opt.label}
              </label>
            ))}
          </fieldset>
        </div>
      )}
    </div>
  );
}
