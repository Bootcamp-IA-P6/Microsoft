#!/usr/bin/env python3
"""Fetch EMT API sample JSON responses into samples/ for the team.

Uses Basic auth (EMT_EMAIL + EMT_PASSWORD in .env). Login responses are saved
with accessToken redacted. Re-run anytime to refresh snapshots:

    python3 scripts/fetch_emt_samples.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

BASE_URL = "https://openapi.emtmadrid.es"
ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"

# Lavapiés — demo area from project README
LON, LAT, RADIUS = -3.7030, 40.4088, 200


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    path = ROOT / ".env"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def api_call(
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict | None = None,
) -> dict:
    url = f"{BASE_URL}{path}"
    args = ["curl", "-sS", "-X", method, url]
    for k, v in (headers or {}).items():
        args += ["-H", f"{k}: {v}"]
    if body is not None:
        args += ["-H", "Content-Type: application/json", "-d", json.dumps(body)]
    out = subprocess.run(args, capture_output=True, text=True, check=False)
    if out.returncode != 0:
        raise RuntimeError(f"{method} {path} curl failed: {out.stderr}")
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{method} {path} non-JSON: {out.stdout[:200]}") from exc


def redact_tokens(obj: object) -> object:
    if isinstance(obj, dict):
        return {
            k: ("***REDACTED***" if k.lower() == "accesstoken" else redact_tokens(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [redact_tokens(x) for x in obj]
    return obj


def save(name: str, payload: dict) -> Path:
    SAMPLES.mkdir(parents=True, exist_ok=True)
    path = SAMPLES / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return path


def login_basic(email: str, password: str) -> tuple[str, dict]:
    raw = api_call(
        "GET",
        "/v1/mobilitylabs/user/login/",
        headers={"email": email, "password": password},
    )
    code = raw.get("code")
    if code not in ("00", "01"):
        raise RuntimeError(f"Basic login failed: code={code} desc={raw.get('description')}")
    token = raw["data"][0]["accessToken"]
    return token, raw


def main() -> int:
    env = load_env()
    email = env.get("EMT_EMAIL", "")
    password = env.get("EMT_PASSWORD", "")
    if not email or not password:
        print(
            "Add EMT_EMAIL and EMT_PASSWORD to .env (local only, never commit).\n"
            "Basic auth is required while passKey login returns code 84.",
            file=sys.stderr,
        )
        return 1

    today = date.today().strftime("%Y%m%d")
    saved: list[str] = []

    hello = api_call("GET", "/v1/hello/")
    saved.append(str(save("01_hello.json", hello)))

    token, login_raw = login_basic(email, password)
    saved.append(str(save("02_login_basic.json", redact_tokens(login_raw))))

    stops = api_call(
        "GET",
        f"/v2/transport/busemtmad/stops/arroundxy/{LON}/{LAT}/{RADIUS}/",
        headers={"accessToken": token},
    )
    saved.append(str(save("03_stops_arroundxy_lavapies.json", stops)))

    stop_ids: list[str] = []
    for row in stops.get("data") or []:
        sid = row.get("stopId")
        if sid and sid not in stop_ids:
            stop_ids.append(str(sid))
        if len(stop_ids) >= 3:
            break
    if not stop_ids:
        print("No stops in arroundxy response", file=sys.stderr)
        return 1

    arrives_body = {
        "cultureInfo": "es",
        "Text_StopRequired_YN": "Y",
        "Text_EstimationsRequired_YN": "Y",
        "Text_LineInfoRequired_YN": "Y",
        "Text_IncidencesRequired_YN": "Y",
        "DateTime_Referenced_Incidencies_YYYYMMDD": today,
    }

    for stop_id in stop_ids:
        # Swagger path includes lineArrive; empty string = all lines at stop
        arrives = api_call(
            "POST",
            f"/v2/transport/busemtmad/stops/{stop_id}/arrives/",
            headers={"accessToken": token},
            body=arrives_body,
        )
        saved.append(str(save(f"04_arrives_stop_{stop_id}.json", arrives)))

        detail = api_call(
            "GET",
            f"/v1/transport/busemtmad/stops/{stop_id}/detail/",
            headers={"accessToken": token},
        )
        saved.append(str(save(f"05_stop_detail_{stop_id}.json", detail)))

    lines_info = api_call(
        "GET",
        f"/v2/transport/busemtmad/lines/info/{today}/",
        headers={"accessToken": token},
    )
    saved.append(str(save("06_lines_info_today.json", lines_info)))

    # incidents for first line seen at first stop
    first_line = None
    for row in stops.get("data") or []:
        for line in row.get("lines") or []:
            first_line = line.get("line") or line.get("label")
            if first_line:
                break
        if first_line:
            break
    if first_line:
        incidents = api_call(
            "GET",
            f"/v1/transport/busemtmad/lines/incidents/{first_line}/",
            headers={"accessToken": token},
        )
        saved.append(str(save(f"07_line_incidents_{first_line}.json", incidents)))

    print(f"Saved {len(saved)} files under {SAMPLES}/")
    for p in saved:
        print(f"  - {Path(p).name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
