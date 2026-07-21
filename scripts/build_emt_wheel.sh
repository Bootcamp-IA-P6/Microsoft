#!/usr/bin/env bash
# Build emt_pipeline wheel and place it in the Fabric Environment CustomLibraries folder.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/env_emt_pipeline.Environment/Libraries/CustomLibraries"

cd "$ROOT"
python3 -m pip install --quiet build
rm -rf dist build *.egg-info src/*.egg-info
python3 -m build --wheel

mkdir -p "$DEST"
rm -f "$DEST"/emt_pipeline-*-py3-none-any.whl
# Project name normalizes to emt_pipeline in the wheel filename.
cp -f dist/emt_pipeline-*-py3-none-any.whl "$DEST/"

echo "Installed wheel(s) into:"
ls -1 "$DEST"/emt_pipeline-*-py3-none-any.whl
