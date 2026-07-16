# Frontend — EMT Madrid (Streamlit)

Chat multiidioma para preguntar por llegadas de bus en el centro de Madrid.

## Correr en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

Por defecto arranca en modo `mock` (usa `fixtures_fase2.json`), así que funciona
sin ninguna conexión externa desde el primer momento.

## Estructura

| Archivo | Qué hace |
|---|---|
| `app.py` | Interfaz — chat, idiomas, tamaño de texto, feedback 👍/👎 |
| `agent_client.py` | **Único punto** por donde se conecta al agente real. Aquí van las 2 conexiones pendientes (local y Azure) |
| `mock_client.py` | Backend de datos de prueba (Fase 2), sobre `fixtures_fase2.json` |
| `i18n.py` | Textos de la interfaz en 6 idiomas |
| `feedback_log.jsonl` | Se genera solo, al primer 👍/👎 que alguien dé |

## Cómo activar cada backend

Cambia la variable de entorno antes de correr Streamlit, o edita
`AGENT_BACKEND` directamente en `agent_client.py`:

```bash
# Plan B: agente local de Raúl
AGENT_BACKEND=local streamlit run app.py

# Producción: Data Agent en Azure vía MCP (necesita permisos F4)
AGENT_BACKEND=azure streamlit run app.py
```

Ambas rutas están señaladas con `TODO` dentro de `agent_client.py`, con el
código de ejemplo ya escrito — solo falta descomentar/ajustar cuando estén
las credenciales y el despliegue reales. Si la conexión elegida falla,
la app hace fallback automático a `mock` para que la demo nunca se rompa.

## Despliegue en Streamlit Cloud

1. Sube esta carpeta a la rama del repo.
2. En Streamlit Cloud: New app → apunta a `frontend/app.py`.
3. En **Settings → Secrets**, añade lo que pida `agent_client.py` cuando
   se conecte a Azure (`ANTHROPIC_API_KEY`, `MCP_SERVER_URL`, etc.) —
   nunca credenciales hardcodeadas en el código.
