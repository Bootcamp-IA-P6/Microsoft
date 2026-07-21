#!/usr/bin/env python3
"""Apply fabric_ids.json into all *.Notebook/notebook-content.py dependency metadata.

Environment is intentionally omitted from notebook metadata by default. Bind env via
Workspace default Environment (see fabric_ids.json) to avoid Fabric open-time
rebind that overwrites thin Git content.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDS = json.loads((ROOT / "fabric_ids.json").read_text(encoding="utf-8"))

WS = IDS["workspace_id"]
LH = IDS["lakehouse"]
ENV = IDS["environment"]
BIND_ENV = bool(ENV.get("bind_in_notebook_metadata", False))

LAKEHOUSE_META = f'''# META     "lakehouse": {{
# META       "default_lakehouse": "{LH["id"]}",
# META       "default_lakehouse_name": "{LH["name"]}",
# META       "default_lakehouse_workspace_id": "{WS}",
# META       "known_lakehouses": [
# META         {{
# META           "id": "{LH["id"]}"
# META         }}
# META       ]
# META     }}'''

if BIND_ENV:
    DEPS = f'''{LAKEHOUSE_META},
# META     "environment": {{
# META       "environmentId": "{ENV["logical_id"]}",
# META       "workspaceId": "{WS}"
# META     }}'''
else:
    DEPS = LAKEHOUSE_META

META_BLOCK = f'''# METADATA ********************

# META {{
# META   "kernel_info": {{
# META     "name": "synapse_pyspark"
# META   }},
# META   "dependencies": {{
{DEPS}
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
    if not HEADER_RE.search(text):
        raise SystemExit(f"could not locate METADATA header in {path}")
    updated = HEADER_RE.sub(new_header, text, count=1)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    for path in sorted(ROOT.glob("*.Notebook/notebook-content.py")):
        if patch(path):
            print(f"patched {path.parent.name}")
        else:
            print(f"unchanged {path.parent.name}")
    mode = "notebook-metadata" if BIND_ENV else "workspace-default-only"
    print(
        f"workspace={WS} lakehouse={LH['name']} "
        f"environment={ENV['name']} bind={mode}"
    )


if __name__ == "__main__":
    main()
