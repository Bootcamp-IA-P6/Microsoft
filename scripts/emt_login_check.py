#!/usr/bin/env python3
"""EMT login diagnostics — reads .env safely, never prints secrets or tokens.

Modes (how to use):
  python3 scripts/emt_login_check.py           # Protected only (ClientId + passKey)
  python3 scripts/emt_login_check.py --advanced # Basic + Protected + Advanced (needs email/pw in .env)

Advanced login (email + password + X-ClientId) exposes apiCounter.owner:
  owner=1 → this ClientId is bound to your account
  owner=0 → ClientId is not linked to this account (wrong app / wrong user)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGIN_URL = "https://openapi.emtmadrid.es/v1/mobilitylabs/user/login/"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in (ROOT / ".env").read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def curl_json(headers: dict[str, str]) -> dict | None:
    args = ["curl", "-sS", LOGIN_URL]
    for key, value in headers.items():
        args += ["-H", f"{key}: {value}"]
    out = subprocess.run(args, capture_output=True, text=True)
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None


def api_counter(resp: dict | None) -> dict | None:
    if not resp or not resp.get("data"):
        return None
    return (resp["data"][0] or {}).get("apiCounter")


def report(label: str, resp: dict | None) -> None:
    if resp is None:
        print(f"\n[{label}] non-JSON response")
        return

    counter = api_counter(resp)
    print(f"\n[{label}]")
    print(f"  code={resp.get('code')}")
    print(f"  description={(resp.get('description') or '')[:80]!r}")
    print(f"  token_issued={bool(resp.get('data'))}")
    if counter is not None:
        print(f"  apiCounter.owner={counter.get('owner')!r}  (1=your app, 0=not linked)")
        print(f"  apiCounter.dailyUse={counter.get('dailyUse')!r}")
        print(f"  apiCounter.current={counter.get('current')!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="EMT MobilityLabs login diagnostics")
    parser.add_argument(
        "--advanced",
        action="store_true",
        help="Also run Basic and Advanced (email+password) logins; requires EMT_EMAIL/EMT_PASSWORD in .env",
    )
    args = parser.parse_args()

    env = load_env()
    cid = env.get("EMT_MADRID_CLIENT_ID") or env.get("EMT_CLIENT_ID", "")
    pk = env.get("EMT_MADRID_PASS_KEY") or env.get("EMT_PASS_KEY", "")

    if not cid or not pk:
        print("Missing EMT_MADRID_CLIENT_ID / EMT_MADRID_PASS_KEY in .env", file=sys.stderr)
        return 1

    print(f"clientId len={len(cid)}  passKey len={len(pk)}")

    report("Protected (X-ClientId + passKey)", curl_json({"X-ClientId": cid, "passKey": pk}))

    if not args.advanced:
        print("\nTip: run with --advanced after adding EMT_EMAIL + EMT_PASSWORD to .env")
        return 0

    email = env.get("EMT_EMAIL", "")
    password = env.get("EMT_PASSWORD", "")
    if not email or not password:
        print("\n--advanced needs EMT_EMAIL and EMT_PASSWORD in .env (remove after test)", file=sys.stderr)
        return 1

    report("Basic (email + password)", curl_json({"email": email, "password": password}))
    report(
        "Advanced (email + password + X-ClientId only)",
        curl_json({"email": email, "password": password, "X-ClientId": cid}),
    )
    report(
        "Advanced full (email + password + X-ClientId + passKey)",
        curl_json(
            {
                "email": email,
                "password": password,
                "X-ClientId": cid,
                "passKey": pk,
            }
        ),
    )

    print("\n--- How to read results ---")
    print("  Protected code=00           → app credentials work standalone (what production needs)")
    print("  Advanced full code=00       → account + app credentials are consistent")
    print("  Advanced full code=89       → server rejects ClientId/passKey pair (or app not activated)")
    print("  Advanced (ClientId only)=89 → often means passKey header was missing, not wrong account")
    print("  Remove EMT_EMAIL / EMT_PASSWORD from .env when done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
