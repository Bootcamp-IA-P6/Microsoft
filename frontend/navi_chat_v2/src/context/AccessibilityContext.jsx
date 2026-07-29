import { createContext, useContext, useEffect, useState } from 'react';

// AccessibilityContext centraliza 2 preferencias del usuario:
//   theme: 'light' | 'dark' | 'high-contrast'
//   fontSize: 'normal' | 'large' | 'xlarge'
//
// Se aplican como atributos data-* en <html>, así el CSS entero
// reacciona con selectores simples (ver App.css). Se guardan en
// localStorage para que la preferencia sobreviva entre visitas —
// esto SÍ es apropiado acá porque es la app real desplegada, no un
// entorno de preview con restricciones de storage.

/**
 * @typedef {'dark' | 'high-contrast'} Theme
 * @typedef {'normal' | 'large' | 'xlarge'} FontSize
 * @typedef {{ theme: Theme; fontSize: FontSize; setTheme: (theme: Theme) => void; setFontSize: (fontSize: FontSize) => void; }} AccessibilityContextValue
 */

const STORAGE_KEY = 'navi:accessibility-prefs';

const AccessibilityContext = createContext(/** @type {AccessibilityContextValue | null} */ (null));

function loadInitialPrefs() {
  const fallback = { theme: 'dark', fontSize: 'normal' };
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (parsed.theme === 'light') parsed.theme = 'dark';
      return { ...fallback, ...parsed };
    }
  } catch {
    // localStorage puede fallar en modo privado estricto; seguimos con el default.
  }
  return { ...fallback, theme: 'dark' };
}

export function AccessibilityProvider({ children }) {
  const [prefs, setPrefs] = useState(loadInitialPrefs);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', prefs.theme);
    document.documentElement.setAttribute('data-font-size', prefs.fontSize);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    } catch {
      // no bloquear la app si falla el guardado
    }
  }, [prefs]);

  function setTheme(theme) {
    if (theme === 'dark' || theme === 'high-contrast') {
      setPrefs((p) => ({ ...p, theme }));
    }
  }
  function setFontSize(fontSize) {
    if (fontSize === 'normal' || fontSize === 'large' || fontSize === 'xlarge') {
      setPrefs((p) => ({ ...p, fontSize }));
    }
  }

  return (
    <AccessibilityContext.Provider value={{ ...prefs, setTheme, setFontSize }}>
      {children}
    </AccessibilityContext.Provider>
  );
}

export function useAccessibility() {
  const ctx = useContext(AccessibilityContext);
  if (!ctx) throw new Error('useAccessibility debe usarse dentro de <AccessibilityProvider>');
  return ctx;
}
