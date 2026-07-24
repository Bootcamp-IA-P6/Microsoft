import { useEffect, useRef, useState } from 'react';
import { useTranslation } from '../context/LanguageContext';

// Íconos SVG estándar (línea, stroke=currentColor) — sin librería externa,
// para no sumar una dependencia solo por 2 glifos. Se exportan porque
// SendIcon también se usa en App.tsx para el botón de "Preguntar".

export function MicIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect x="9" y="2" width="6" height="12" rx="3" stroke="currentColor" strokeWidth="2" />
      <path d="M5 11a7 7 0 0 0 14 0" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <line x1="12" y1="18" x2="12" y2="22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <line x1="8" y1="22" x2="16" y2="22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function StopIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" />
    </svg>
  );
}

export function SendIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M12 19V5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M6 11l6-6 6 6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// VoiceInputButton: Web Speech API nativa. Soporte real: Chrome/Edge sí,
// Safari parcial, Firefox NO (el botón no aparece ahí, no rompe la app).
const RECOGNITION_LOCALE = { es: 'es-ES', en: 'en-US', pt: 'pt-PT' };

export default function VoiceInputButton({ onResult, disabled }) {
  const { t, language } = useTranslation();
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(true);
  const [error, setError] = useState(null);
  const recognitionRef = useRef(null);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setIsSupported(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = RECOGNITION_LOCALE[language] || 'es-ES';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
      onResult(event.results[0][0].transcript);
      setIsListening(false);
    };

    recognition.onerror = (event) => {
      setIsListening(false);
      if (event.error === 'not-allowed' || event.error === 'permission-denied') {
        setError(t('voiceErrorPermission'));
      } else if (event.error === 'no-speech') {
        setError(t('voiceErrorNoSpeech'));
      } else {
        setError(t('voiceErrorGeneric'));
      }
    };

    recognition.onend = () => setIsListening(false);

    recognitionRef.current = recognition;
    return () => recognition.abort();
  }, [onResult, language, t]);

  function handleClick() {
    if (!recognitionRef.current || disabled) return;
    setError(null);
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      setIsListening(true);
      recognitionRef.current.start();
    }
  }

  if (!isSupported) return null;

  return (
    <div className="voice-input">
      <button
        type="button"
        className={`voice-input__button ${isListening ? 'voice-input__button--listening' : ''}`}
        onClick={handleClick}
        disabled={disabled}
        aria-pressed={isListening}
        aria-label={isListening ? t('voiceStop') : t('voiceAsk')}
        title={isListening ? t('voiceStop') : t('voiceAsk')}
      >
        {isListening ? <StopIcon /> : <MicIcon />}
      </button>
      {error && (
        <p className="voice-input__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
