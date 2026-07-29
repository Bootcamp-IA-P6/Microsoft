# Guía técnica — instalación y ejecución

Esta guía documenta cómo levantar NAVI **tal como quedó implementado**, no la propuesta de referencia. Cubre el camino de producción (frontend → Fabric UDF) y el fallback local de testing.

---

## 1. Requisitos previos

- **Node.js** ≥ 18 y npm
- **Python** ≥ 3.10 (solo si vas a usar el fallback local)
- Cuenta en el **tenant de Microsoft 365 / Fabric** del proyecto, con acceso al workspace
- **Azure CLI** instalado y con sesión iniciada (`az login`) — solo necesario para el fallback local
- Registro de app en **Microsoft Entra ID** con permiso delegado `UserDataFunction.Execute.All` (Power BI Service) — ya configurado para el proyecto; pide el `Client ID` / `Tenant ID` al equipo si no los tienes
- Token de la **API EMT Madrid** (MobilityLabs) — solo necesario si vas a tocar los notebooks de ingesta

---

## 2. Clonar y ubicar el proyecto vigente

```bash
git clone https://github.com/Bootcamp-IA-P6/Microsoft.git
cd Microsoft/frontend/navi_chat_v2
```

> `frontend/navi_chat_v2` es la app vigente en `main`. `frontend/navi-chat` (sin `_v2`) es una versión anterior, conservada como referencia histórica — no la levantes para la demo.

---

## 3. Variables de entorno

### 3.1 Frontend (`frontend/navi_chat_v2/.env`)

```env
VITE_UDF_CLIENT_ID=<Application (client) ID de la app registration en Entra ID>
VITE_UDF_TENANT_ID=<Directory (tenant) ID>
VITE_UDF_PUBLIC_URL=<URL pública del Fabric User Data Function>
```

Estas tres variables son las únicas necesarias para el camino de producción (frontend → UDF directo).

### 3.2 Fallback local (`.env` en la raíz del repo)

```env
# API EMT Madrid (MobilityLabs)
EMT_CLIENT_ID=
EMT_MADRID_PASS_KEY=

# Fabric Data Agent vía MCP
FABRIC_MCP_URL=https://api.fabric.microsoft.com/v1/mcp/workspaces/{WorkspaceId}/dataagents/{DataAgentId}/agent

# Backend local de testing
DEMO_API_KEY=<clave arbitraria para proteger el endpoint local>
```

> ⚠️ Nota conocida (Windows/Git Bash): si `SSL_CERT_FILE` apunta a una ruta rota, `agent_mcp.py` la ignora automáticamente al arrancar — no hace falta limpiarla a mano.

---

## 4. Levantar el frontend (camino de producción)

```bash
cd frontend/navi_chat_v2
npm install
npm run dev
```

Esto ejecuta `rayfin up --exclude-services staticHosting && vite` — Rayfin resuelve la parte de auth Fabric localmente y Vite sirve la app en `http://localhost:5173`.

Al abrir la app:
1. El login de Microsoft se dispara vía `msalInstance.loginRedirect` (ver `src/main.tsx`).
2. Tras autenticarse, cada pregunta al chat obtiene un token con scope `UserDataFunction.Execute.All` (`src/services/udfAuth.ts`) y llama directo a `VITE_UDF_PUBLIC_URL` (`src/services/agentService.ts`).
3. No hace falta backend local corriendo para este flujo.

**Build para despliegue en Fabric (static hosting vía Rayfin):**

```bash
npm run build:fabric
```

Los orígenes permitidos (CORS / redirect URIs) están fijados en `rayfin/rayfin.yml` y en `server.py` — si despliegas a una URL nueva, añádela ahí antes de probar.

---

## 5. Fallback local (backend de testing, sin depender del UDF)

Útil para probar el Data Agent directamente desde tu máquina, sin pasar por el UDF de Fabric — por ejemplo si el UDF está caído o quieres depurar la respuesta del agente antes de que llegue al frontend.

```bash
# desde la raíz del repo
python -m venv .venv
source .venv/bin/activate  # o .venv\Scripts\activate en Windows
pip install fastapi uvicorn python-dotenv azure-identity mcp

cd frontend/navi_chat_v2
uvicorn server:app --host 0.0.0.0 --port 8000
```

Requiere sesión activa de `az login` (usa `AzureCliCredential`, ver `agent_mcp.py`) y las variables `FABRIC_MCP_URL` / `DEMO_API_KEY` cargadas.

Prueba rápida:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-Demo-Key: <tu DEMO_API_KEY>" \
  -d '{"question": "¿Cuánto tarda el próximo bus en Lavapiés?", "language": "es"}'
```

### 5.1 Probar solo la autenticación Entra ID → UDF (sin frontend)

Script aislado, útil para validar credenciales antes de tocar el frontend:

```bash
cd frontend/navi_chat_v2
UDF_TEST_CLIENT_ID=<client id> \
UDF_TEST_TENANT_ID=<tenant id> \
UDF_PUBLIC_URL=<url del UDF> \
node --env-file=.env test-udf-entra.mjs
```

Sigue el flujo de device code: abre `https://login.microsoft.com/device`, introduce el código mostrado en consola, y el script hace una llamada de prueba al UDF con el token obtenido.

---

## 6. Pipeline de datos (notebooks en Fabric)

Los notebooks viven en `notebooks/` y se ejecutan **dentro del workspace de Fabric**, no localmente:

| Notebook | Qué hace | Cadencia |
|---|---|---|
| `nb_bootstrap_gtfs_silver.py` | Bootstrap GTFS estático → seed de `silver_arrives` (paradas/líneas in-scope) | 1×/día |
| `nb_create_tables.py` | Creación/esquema de las tablas Delta del lakehouse | manual / setup |
| `nb_ingest_emt_arrives.py` | Poll de `arrives` (S1) y `servicealerts` (S2) → `bronze_emt_raw` | ~60s / ~300s |
| `nb_transform_bronze_silver_gold.py` / `_optimized.py` | Transformación Bronze → `silver_arrives` + `silver_alerts` → MERGE `gold_emt_stop_line` | según trigger del pipeline |

Detalle completo de columnas, PKs y reglas de negocio: [`docs/data-source-contract-v4.md`](data-source-contract-v4.md).

El **Semantic Model (Direct Lake)** se monta sobre `gold_emt_stop_line` dentro de Fabric y es lo que el Data Agent consulta — no hay paso local para esto, se configura desde el portal de Fabric.

---

## 7. Troubleshooting conocido

| Síntoma | Causa | Solución |
|---|---|---|
| `SSL_CERT_FILE` rompe la conexión MCP en Windows/Git Bash | Variable de entorno heredada apuntando a una ruta inválida | `agent_mcp.py` ya la borra automáticamente si no existe el archivo; si persiste, `unset SSL_CERT_FILE` antes de correr |
| Error 401 al llamar al UDF desde el frontend | Token expirado o `redirectUri` no está en `allowedRedirectUris` de `rayfin.yml` | Verifica que la URL desde la que accedes esté listada; si no, `loginRedirect` fallará silenciosamente |
| CORS bloqueando `/api/chat` en el fallback local | Origen no listado en `server.py` (`CORSMiddleware`) | Añade tu origen a la lista `allow_origins` |
| El mapa no traza la ruta real del bus | Coordenadas de paradas son mock (`src/utils/geoData.ts`) mientras se implementa la extensión de `gold_emt_stop_line` con `bus_lat/lon` | Decisión ya cerrada — ver README, sección "Decisiones de cierre", punto 4. El mock queda obsoleto en cuanto la extensión de Gold esté disponible |
| Variables hardcodeadas en el UDF | Deuda técnica temporal de las pruebas de conexión inicial | Pendiente de mover a configuración antes de cualquier uso post-demo |

---

*Guía de cierre — válida para el estado del sistema a 27/07/2026.*
