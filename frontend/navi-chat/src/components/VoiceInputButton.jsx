import { useEffect, useRef, useState } from 'react';
import { useTranslation } from '../context/LanguageContext';

// VoiceInputButton: usa la Web Speech API nativa del navegador.
// Soporte real: Chrome/Edge sí, Safari parcial, Firefox NO (por eso el
// chequeo de isSupported, con fallback a "solo texto" en vez de romper la app).
//
// El idioma de reconocimiento (recognition.lang) sigue el idioma activo de
// la UI, así "27" en inglés y "27" en español se transcriben igual de bien
// según lo que el usuario esté hablando.

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
      >
        <span aria-hidden="true">{isListening ? '●' : '🎙'}</span>
      </button>
      {error && (
        <p className="voice-input__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
