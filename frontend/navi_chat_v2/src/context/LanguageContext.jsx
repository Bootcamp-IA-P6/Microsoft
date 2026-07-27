import { createContext, useContext, useEffect, useState } from 'react';
import { translations, detectDefaultLanguage } from '../i18n/translations';

const STORAGE_KEY = 'navi:language';

const LanguageContext = createContext(null);

function loadInitialLanguage() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && translations[saved]) return saved;
  } catch {
    // seguimos con la detección por navegador si falla localStorage
  }
  return detectDefaultLanguage();
}

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(loadInitialLanguage);

  useEffect(() => {
    document.documentElement.setAttribute('lang', language);
    try {
      localStorage.setItem(STORAGE_KEY, language);
    } catch {
      // no bloquear la app si falla el guardado
    }
  }, [language]);

  function setLanguage(lang) {
    if (translations[lang]) setLanguageState(lang);
  }

  return (
    <LanguageContext.Provider value={{ language, setLanguage }}>
      {children}
    </LanguageContext.Provider>
  );
}

// useTranslation(): devuelve t(key, ...args) — si la clave falta en el
// idioma activo, cae de vuelta a español antes que romper el layout
// mostrando la clave cruda.
export function useTranslation() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useTranslation debe usarse dentro de <LanguageProvider>');

  function t(key, ...args) {
    const dict = translations[ctx.language] || translations.es;
    const entry = dict[key] ?? translations.es[key] ?? key;
    return typeof entry === 'function' ? entry(...args) : entry;
  }

  return { t, language: ctx.language, setLanguage: ctx.setLanguage };
}
