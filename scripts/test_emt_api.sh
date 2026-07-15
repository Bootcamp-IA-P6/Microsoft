#!/usr/bin/env bash
# ------------------------------------------------------------
# - Quick smoke test for EMT Madrid OpenAPI using .env credentials.
# - how to use: ./scripts/test_emt_api.sh
# - x-ClientId looks like a UUID (~36 chars), copied from Mobility Labs app panel
# - passKey copied alone, no labels/extra text/spaces
# - app created at https://mobilitylabs.emtmadrid.es (Mis Aplicaciones)
# - docs: https://apidocs.emtmadrid.es/#api-Block_1_User_identity-login
# ------------------------------------------------------------

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Missing .env in repo root" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

CLIENT_ID="${EMT_MADRID_CLIENT_ID:-${EMT_CLIENT_ID:-}}"
PASS_KEY="${EMT_MADRID_PASS_KEY:-${EMT_PASS_KEY:-}}"

trim() {
  # remove surrounding quotes and whitespace
  local v="$1"
  v="${v%\"}"; v="${v#\"}"
  v="${v%\'}"; v="${v#\'}"
  printf '%s' "$v" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

CLIENT_ID="$(trim "$CLIENT_ID")"
PASS_KEY="$(trim "$PASS_KEY")"

if [[ -z "$CLIENT_ID" || -z "$PASS_KEY" ]]; then
  echo "Set EMT_MADRID_CLIENT_ID + EMT_MADRID_PASS_KEY in .env" >&2
  echo "(aliases: EMT_CLIENT_ID + EMT_PASS_KEY)" >&2
  exit 1
fi

redact_json() {
  python3 -c '
import json, sys
data = json.load(sys.stdin)
SENSITIVE = {"accesstoken", "passkey", "x-apikey"}

def walk(obj):
    if isinstance(obj, dict):
        return {k: ("***redacted***" if k.lower() in SENSITIVE else walk(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [walk(x) for x in obj]
    return obj

print(json.dumps(walk(data), indent=2, ensure_ascii=False))
'
}

echo "1) GET /v1/hello/"
curl -sS -L "https://openapi.emtmadrid.es/v1/hello/" | redact_json

echo
echo "2) GET /v1/mobilitylabs/user/login/  (X-ClientId + passKey)"
LOGIN_JSON="$(curl -sS -X GET "https://openapi.emtmadrid.es/v1/mobilitylabs/user/login/" \
  -H "X-ClientId: ${CLIENT_ID}" \
  -H "passKey: ${PASS_KEY}")"

echo "$LOGIN_JSON" | redact_json

CODE="$(echo "$LOGIN_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("code",""))')"
if [[ "$CODE" != "00" && "$CODE" != "01" ]]; then
  echo
  echo "Login failed (code=${CODE}). Check:" >&2
  echo "  - x-ClientId looks like a UUID (~36 chars), copied from Mobility Labs app panel" >&2
  echo "  - passKey copied alone, no labels/extra text/spaces" >&2
  echo "  - app created at https://mobilitylabs.emtmadrid.es (Mis Aplicaciones)" >&2
  echo "  - docs: https://apidocs.emtmadrid.es/#api-Block_1_User_identity-login" >&2
  exit 1
fi

TOKEN="$(echo "$LOGIN_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"][0]["accessToken"])')"

echo
echo "3) GET /v2/transport/busemtmad/stops/arroundxy/...  (near Lavapiés)"
STOPS_JSON="$(curl -sS "https://openapi.emtmadrid.es/v2/transport/busemtmad/stops/arroundxy/-3.7030/40.4088/200/" \
  -H "accessToken: ${TOKEN}")"
echo "$STOPS_JSON" | python3 -c 'import json,sys; d=json.load(sys.stdin); d["data"]=d.get("data",[])[:2]; print(json.dumps(d, indent=2, ensure_ascii=False))'

STOP_ID="$(echo "$STOPS_JSON" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["data"][0]["stopId"])')"
echo "Using stopId=${STOP_ID}"

echo
echo "4) POST /v2/transport/busemtmad/stops/${STOP_ID}/arrives/"
curl -sS -X POST "https://openapi.emtmadrid.es/v2/transport/busemtmad/stops/${STOP_ID}/arrives/" \
  -H "accessToken: ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"cultureInfo":"es","Text_StopRequired_YN":"Y","Text_EstimationsRequired_YN":"Y","Text_LineInfoRequired_YN":"Y","Text_IncidencesRequired_YN":"Y"}' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin);
for block in d.get("data",[]):
  if isinstance(block.get("Arrive"), list):
    block["Arrive"]=block["Arrive"][:3]
print(json.dumps(d, indent=2, ensure_ascii=False))'

echo
echo "OK: credentials work and real-time bus data is reachable."
