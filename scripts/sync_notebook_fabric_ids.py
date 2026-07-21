#!/usr/bin/env python3
"""Apply fabric_ids.json into all *.Notebook/notebook-content.py dependency metadata."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDS = json.loads((ROOT / "fabric_ids.json").read_text(encoding="utf-8"))

WS = IDS["workspace_id"]
LH = IDS["lakehouse"]
ENV = IDS["environment"]

META_BLOCK = f'''# METADATA ********************

# META {{
# META   "kernel_info": {{
# META     "name": "synapse_pyspark"
# META   }},
# META   "dependencies": {{
# META     "lakehouse": {{
# META       "default_lakehouse": "{LH["id"]}",
# META       "default_lakehouse_name": "{LH["name"]}",
# META       "default_lakehouse_workspace_id": "{WS}",
# META       "known_lakehouses": [
# META         {{
# META           "id": "{LH["id"]}"
# META         }}
# META       ]
# META     }},
# META     "environment": {{
# META       "environmentId": "{ENV["logical_id"]}",
# META       "workspaceId": "{WS}"
# META     }}
# META   }}
# META }}
'''

HEADER_RE = re.compile(
    r"# Fabric notebook source\n\n# METADATA \*{20,}.*?# META \}\n",
    re.DOTALL,
)


def patch(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("# Fabric notebook source"):
        raise SystemExit(f"unexpected notebook header: {path}")
    new_header = f"# Fabric notebook source\n\n{META_BLOCK}"
    if HEADER_RE.search(text):
        updated = HEADER_RE.sub(new_header, text, count=1)
    else:
        # fallback: replace first METADATA section roughly
        updated = text
    if updated == text and META_BLOCK.strip() in text:
        return False
    if not HEADER_RE.search(text):
        raise SystemExit(f"could not locate METADATA header in {path}")
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    changed = []
    for path in sorted(ROOT.glob("*.Notebook/notebook-content.py")):
        if patch(path):
            changed.append(path.parent.name)
            print(f"patched {path.parent.name}")
        else:
            print(f"unchanged {path.parent.name}")
    print(
        f"workspace={WS} lakehouse={LH['name']} "
        f"environment={ENV['name']} ({ENV['logical_id']})"
    )
    if not changed:
        print("no files changed")


if __name__ == "__main__":
    main()
