#!/usr/bin/env python3
"""Quick smoke test for EMT Madrid OpenAPI using .env credentials."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import urllib.error
import urllib.request

BASE_URL = "https://openapi.emtmadrid.es"
ROOT = Path(__file__).resolve().parents[1]


def load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        raise FileNotFoundError(f"Missing {env_path}")

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def request(
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict | None = None,
) -> dict:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req_headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = resp.read().decode()
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode()
        raise RuntimeError(f"{method} {path} -> HTTP {exc.code}: {payload}") from exc

    return json.loads(payload)


def redact(value: object) -> object:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key.lower() in {"accesstoken", "passkey", "x-apikey"}:
                out[key] = "***redacted***"
            else:
                out[key] = redact(item)
        return out
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def main() -> int:
    load_env()
    client_id = os.environ.get("EMT_MADRID_CLIENT_ID") or os.environ.get("EMT_CLIENT_ID", "")
    pass_key = os.environ.get("EMT_MADRID_PASS_KEY") or os.environ.get("EMT_PASS_KEY", "")
    if not client_id or not pass_key:
        print(
            "Set EMT_MADRID_CLIENT_ID + EMT_MADRID_PASS_KEY (or EMT_CLIENT_ID + EMT_PASS_KEY) in .env",
            file=sys.stderr,
        )
        return 1

    print("1) GET /v1/hello/")
    hello = request("GET", "/v1/hello/")
    print(json.dumps(redact(hello), indent=2, ensure_ascii=False))

    print("\n2) GET /v1/mobilitylabs/user/login/  (X-ClientId + passKey)")
    login = request(
        "GET",
        "/v1/mobilitylabs/user/login/",
        headers={"X-ClientId": client_id, "passKey": pass_key},
    )
    print(json.dumps(redact(login), indent=2, ensure_ascii=False))

    if login.get("code") not in ("00", "01"):
        print("Login failed", file=sys.stderr)
        return 1

    token = login["data"][0]["accessToken"]

    print("\n3) GET /v2/transport/busemtmad/stops/arroundxy/...  (near Lavapiés)")
    stops = request(
        "GET",
        "/v2/transport/busemtmad/stops/arroundxy/-3.7030/40.4088/200/",
        headers={"accessToken": token},
    )
    preview = redact(stops)
    if isinstance(preview.get("data"), list):
        preview["data"] = preview["data"][:3]
    print(json.dumps(preview, indent=2, ensure_ascii=False))

    stop_id = stops["data"][0]["stopId"] if stops.get("data") else None
    if not stop_id:
        print("No stops found near Lavapiés", file=sys.stderr)
        return 1

    print(f"\n4) POST /v2/transport/busemtmad/stops/{stop_id}/arrives/")
    arrives = request(
        "POST",
        f"/v2/transport/busemtmad/stops/{stop_id}/arrives/",
        headers={"accessToken": token},
        body={
            "cultureInfo": "es",
            "Text_StopRequired_YN": "Y",
            "Text_EstimationsRequired_YN": "Y",
            "Text_LineInfoRequired_YN": "Y",
            "Text_IncidencesRequired_YN": "Y",
        },
    )
    preview = redact(arrives)
    if isinstance(preview.get("data"), list):
        for item in preview["data"]:
            if isinstance(item.get("Arrive"), list):
                item["Arrive"] = item["Arrive"][:3]
    print(json.dumps(preview, indent=2, ensure_ascii=False))

    print("\nOK: credentials work and real-time bus data is reachable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
