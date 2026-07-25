# Frontend — NAVI tu copiloto de movilidad [EMT Madrid] (Streamlit)

Chat multiidioma para preguntar por llegadas de autobús en el centro de Madrid.

## Cómo correrlo en local

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

Por defecto arranca en modo `mock` (usa `fixtures_fase2.json`), así que funciona
sin ninguna conexión externa desde el primer momento.

## Funcionalidades actuales

- Interfaz de chat con mensajes del usuario y del asistente.
- Soporte multiidioma con varios idiomas disponibles en el selector de la barra lateral.
- Modo de color accesible con paleta de alto contraste y modo oscuro.
- Ajuste de tamaño de texto para mejorar la legibilidad.
- Feedback con botones 👍/👎 para registrar opinión de las respuestas.
- Botón de limpiar chat para reiniciar la conversación.
- Botón de voz integrado en el formulario de entrada.
- Estilo visual adaptado con colores de la paleta de la aplicación.

## Estructura del frontend

| Archivo | Qué hace |
|---|---|
| `app.py` | Interfaz principal: chat, selector de idioma, temas, tamaño de texto, feedback y formulario de entrada |
| `agent_client.py` | Punto de conexión con el agente real; aquí se gestiona la comunicación con los backends disponibles |
| `mock_client.py` | Backend de datos de prueba basado en `fixtures_fase2.json` |
| `idioms_dict.py` | Diccionario de textos de la interfaz en varios idiomas |
| `themes.py` | Definición de paletas visuales para los modos colorblind y dark |
| `feedback_log.jsonl` | Registro de feedback generado automáticamente al usar 👍/👎 |

## Idiomas disponibles

El selector de idioma incluye:

- Español (`es`)
- English (`en`)
- Français (`fr`)
- Deutsch (`de`)
- Italiano (`it`)
- Português (`pt`)
- Português (Brasil) (`pt-BR`)

Los textos de la interfaz se gestionan desde `idioms_dict.py`.

## Personalización visual

La app incluye dos modos de color en `themes.py`:

- `colorblind`: modo por defecto, con paleta accesible y alto contraste.
- `dark`: tema oscuro con colores contrastados para mejor legibilidad.

Además, el tamaño de texto puede ajustarse entre `normal` y `large` desde la barra lateral.

## Cómo activar cada backend

Cambia la variable de entorno antes de correr Streamlit, o edita
`AGENT_BACKEND` directamente en `agent_client.py`:

```bash
# Agente local
AGENT_BACKEND=local streamlit run app.py

# Producción: Data Agent en Azure vía MCP (necesita permisos F4)
AGENT_BACKEND=azure streamlit run app.py
```

Si la conexión elegida falla, la app hace fallback automático a `mock` para que la demo no se rompa.

## Despliegue en Streamlit Cloud

1. Sube esta carpeta a la rama del repositorio.
2. En Streamlit Cloud: New app → apunta a `frontend/app.py`.
3. En **Settings → Secrets**, añade lo que pida `agent_client.py` cuando
   se conecte a Azure (`ANTHROPIC_API_KEY`, `MCP_SERVER_URL`, etc.).
   Nunca guardes credenciales hardcodeadas en el código.
