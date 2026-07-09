#!/usr/bin/env python3
"""Inspect EMT credentials in .env WITHOUT printing their values.

Checks for hidden/whitespace/non-hex characters that could cause auth failures.
Only prints shape/statistics, never the secret itself.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_raw_env() -> dict[str, str]:
    env: dict[str, str] = {}
    raw = (ROOT / ".env").read_bytes().decode("utf-8", errors="replace")
    # detect line ending style
    print(f".env line endings: CRLF={'\\r\\n' in raw}  LF-only={'\\n' in raw and '\\r\\n' not in raw}")
    for line in raw.splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v  # keep value exactly, no stripping
    return env


def describe(name: str, value_with_ws: str) -> None:
    v = value_with_ws
    stripped = v.strip()
    leading = len(v) - len(v.lstrip())
    trailing = len(v) - len(v.rstrip())
    # any quotes?
    quoted = stripped[:1] in "\"'" or stripped[-1:] in "\"'"
    core = stripped.strip("\"'")

    is_hex = bool(re.fullmatch(r"[0-9A-Fa-f]+", core))
    is_uuid = bool(re.fullmatch(r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}", core))

    # detect any non-printable / non-ascii / weird unicode
    weird = []
    for ch in core:
        cp = ord(ch)
        if cp < 32 or cp == 127:
            weird.append(f"CTRL(U+{cp:04X})")
        elif cp > 126:
            weird.append(f"{unicodedata.name(ch, 'UNKNOWN')}(U+{cp:04X})")

    print(f"\n[{name}]")
    print(f"  raw_len={len(v)}  stripped_len={len(core)}")
    print(f"  leading_ws={leading}  trailing_ws={trailing}  wrapped_in_quotes={quoted}")
    print(f"  all_hex={is_hex}  uuid_format={is_uuid}")
    print(f"  non-ascii/hidden chars: {weird[:10] if weird else 'none'}")


def main() -> int:
    env = load_raw_env()
    cid = env.get("EMT_MADRID_CLIENT_ID", env.get("EMT_CLIENT_ID", ""))
    pk = env.get("EMT_MADRID_PASS_KEY", env.get("EMT_PASS_KEY", ""))
    if not cid or not pk:
        print("Missing credentials in .env")
        return 1
    describe("clientId", cid)
    describe("passKey", pk)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
