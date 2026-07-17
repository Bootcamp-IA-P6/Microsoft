"""
Config centralizado del proyecto EMT Madrid.

Carga variables desde .env (en la raiz del proyecto, junto a agents/, frontend/, etc.)
Todos los archivos que necesiten claves deben importar de aca, nunca hardcodear.

Uso:
    from config import GROQ_API_KEY, MODEL
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# config.py vive en la RAIZ del proyecto (junto a agents/, frontend/, .env).
# El .env esta en el mismo directorio que este archivo.
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

# --- Groq / LLM ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

# --- EMT Madrid API ---
EMT_CLIENT_ID = os.environ.get("EMT_CLIENT_ID", "")
EMT_MADRID_PASS_KEY = os.environ.get("EMT_MADRID_PASS_KEY", "")
EMT_EMAIL = os.environ.get("EMT_EMAIL", "")
EMT_PASSWORD = os.environ.get("EMT_PASSWORD", "")

# --- Azure OpenAI / Fabric (Fase 3, aun sin usar) ---
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY", "")


def require_groq_key():
    """Llamar al arrancar cualquier script que use Groq, para fallar rapido
    con un mensaje claro en vez de un error críptico de la librería."""
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY no está definida. Copiá .env.example a .env "
            "en la raíz del proyecto y completá tu clave."
        )