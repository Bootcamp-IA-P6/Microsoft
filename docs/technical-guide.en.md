# Technical guide — installation and run

This guide documents how to run NAVI **as it was actually implemented**, not the reference proposal. It covers the production path (frontend → Fabric UDF) and the local testing fallback.

---

## 1. Prerequisites

- **Node.js** ≥ 18 and npm
- **Python** ≥ 3.10 (only if you're going to use the local fallback)
- Account on the project's **Microsoft 365 / Fabric tenant**, with access to the workspace
- **Azure CLI** installed and signed in (`az login`) — only needed for the local fallback
- App registration in **Microsoft Entra ID** with the delegated permission `UserDataFunction.Execute.All` (Power BI Service) — already configured for the project; ask the team for the `Client ID` / `Tenant ID` if you don't have them
- **EMT Madrid API** token (MobilityLabs) — only needed if you're going to work on the ingestion notebooks

---

## 2. Clone and locate the current project

```bash
git clone https://github.com/Bootcamp-IA-P6/Microsoft.git
cd Microsoft/frontend/navi_chat_v2
```

> `frontend/navi_chat_v2` is the current app on `main`. `frontend/navi-chat` (without `_v2`) is a previous version, kept as a historical reference — don't run it for the demo.

---

## 3. Environment variables

### 3.1 Frontend (`frontend/navi_chat_v2/.env`)

```env
VITE_UDF_CLIENT_ID=<Application (client) ID of the app registration in Entra ID>
VITE_UDF_TENANT_ID=<Directory (tenant) ID>
VITE_UDF_PUBLIC_URL=<Public URL of the Fabric User Data Function>
```

These three variables are the only ones needed for the production path (frontend → direct UDF).

### 3.2 Local fallback (`.env` at the repo root)

```env
# EMT Madrid API (MobilityLabs)
EMT_CLIENT_ID=
EMT_MADRID_PASS_KEY=

# Fabric Data Agent via MCP
FABRIC_MCP_URL=https://api.fabric.microsoft.com/v1/mcp/workspaces/{WorkspaceId}/dataagents/{DataAgentId}/agent

# Local testing backend
DEMO_API_KEY=<arbitrary key to protect the local endpoint>
```

> ⚠️ Known note (Windows/Git Bash): if `SSL_CERT_FILE` points to a broken path, `agent_mcp.py` automatically ignores it on startup — no need to unset it by hand.

---

## 4. Run the frontend (production path)

```bash
cd frontend/navi_chat_v2
npm install
npm run dev
```

This runs `rayfin up --exclude-services staticHosting && vite` — Rayfin resolves the Fabric auth part locally and Vite serves the app at `http://localhost:5173`.

When you open the app:
1. Microsoft login is triggered via `msalInstance.loginRedirect` (see `src/main.tsx`).
2. After authenticating, every chat question fetches a token with the `UserDataFunction.Execute.All` scope (`src/services/udfAuth.ts`) and calls `VITE_UDF_PUBLIC_URL` directly (`src/services/agentService.ts`).
3. No local backend needs to be running for this flow.

**Build for deployment to Fabric (static hosting via Rayfin):**

```bash
npm run build:fabric
```

Allowed origins (CORS / redirect URIs) are set in `rayfin/rayfin.yml` and in `server.py` — if you deploy to a new URL, add it there before testing.

---

## 5. Local fallback (testing backend, without depending on the UDF)

Useful for testing the Data Agent directly from your machine, without going through the Fabric UDF — for example, if the UDF is down or you want to debug the agent's answer before it reaches the frontend.

```bash
# from the repo root
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install fastapi uvicorn python-dotenv azure-identity mcp

cd frontend/navi_chat_v2
uvicorn server:app --host 0.0.0.0 --port 8000
```

Requires an active `az login` session (uses `AzureCliCredential`, see `agent_mcp.py`) and the `FABRIC_MCP_URL` / `DEMO_API_KEY` variables loaded.

Quick test:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-Demo-Key: <your DEMO_API_KEY>" \
  -d '{"question": "How long until the next bus arrives at Lavapiés?", "language": "es"}'
```

### 5.1 Test only the Entra ID → UDF authentication (no frontend)

Standalone script, useful for validating credentials before touching the frontend:

```bash
cd frontend/navi_chat_v2
UDF_TEST_CLIENT_ID=<client id> \
UDF_TEST_TENANT_ID=<tenant id> \
UDF_PUBLIC_URL=<UDF url> \
node --env-file=.env test-udf-entra.mjs
```

Follows the device code flow: open `https://login.microsoft.com/device`, enter the code shown in the console, and the script makes a test call to the UDF with the token it obtained.

---

## 6. Data pipeline (notebooks on Fabric)

The notebooks live in `notebooks/` and run **inside the Fabric workspace**, not locally:

| Notebook | What it does | Cadence |
|---|---|---|
| `nb_bootstrap_gtfs_silver.py` | Bootstrap static GTFS → seeds `silver_arrives` (in-scope stops/lines) | 1×/day |
| `nb_create_tables.py` | Creates/schemas the lakehouse's Delta tables | manual / setup |
| `nb_ingest_emt_arrives.py` | Polls `arrives` (S1) and `servicealerts` (S2) → `bronze_emt_raw` | ~60s / ~300s |
| `nb_transform_bronze_silver_gold.py` / `_optimized.py` | Transforms Bronze → `silver_arrives` + `silver_alerts` → MERGE into `gold_emt_stop_line` | per pipeline trigger |

Full detail on columns, PKs, and business rules: [`docs/data-source-contract-v4.md`](data-source-contract-v4.md).

The **Semantic Model (Direct Lake)** is built on top of `gold_emt_stop_line` inside Fabric and is what the Data Agent queries — there's no local step for this, it's configured from the Fabric portal.

---

## 7. Known troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `SSL_CERT_FILE` breaks the MCP connection on Windows/Git Bash | An inherited environment variable pointing to an invalid path | `agent_mcp.py` already clears it automatically if the file doesn't exist; if it persists, `unset SSL_CERT_FILE` before running |
| 401 error when calling the UDF from the frontend | Expired token, or the `redirectUri` isn't in `rayfin.yml`'s `allowedRedirectUris` | Check that the URL you're accessing from is listed; otherwise `loginRedirect` will fail silently |
| CORS blocking `/api/chat` on the local fallback | Origin not listed in `server.py` (`CORSMiddleware`) | Add your origin to the `allow_origins` list |
| The map doesn't trace the bus's real route | Stop coordinates are mocked (`src/utils/geoData.ts`) while the `gold_emt_stop_line` extension with `bus_lat/lon` is being implemented | Decision already closed — see README, "Closing decisions" section, item 4. The mock becomes obsolete once the Gold extension is available |
| Hardcoded variables in the UDF | Temporary technical debt from the initial connection testing | Pending a move to configuration before any use beyond the demo |

---

*Closing guide — valid for the system's state as of 2026-07-27.*
