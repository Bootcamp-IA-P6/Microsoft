"""Ensure Lakehouse Files/python is on sys.path for `import pipeline`."""
from __future__ import annotations

import sys

DEFAULT_FILES_PYTHON = "/lakehouse/default/Files/python"


def ensure_pipeline_on_path(files_python: str = DEFAULT_FILES_PYTHON) -> str:
    if files_python not in sys.path:
        sys.path.insert(0, files_python)
    return files_python
