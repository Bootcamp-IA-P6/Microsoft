"""Fabric Variable Library helpers."""
from __future__ import annotations


def load_variable_library(library_name: str):
    try:
        import notebookutils

        return notebookutils.variableLibrary.getLibrary(library_name)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Cannot load Variable Library '{library_name}': {exc}") from exc


def lib_get(lib, name: str) -> str:
    if hasattr(lib, "getVariable"):
        try:
            return str(lib.getVariable(name) or "").strip()
        except Exception:  # noqa: BLE001
            pass
    try:
        return str(lib[name] or "").strip()
    except Exception:  # noqa: BLE001
        pass
    return str(getattr(lib, name, None) or "").strip()


def load_emt_credentials(library_name: str) -> tuple[str, str]:
    lib = load_variable_library(library_name)
    client_id = lib_get(lib, "EMT_CLIENT_ID")
    pass_key = lib_get(lib, "EMT_MADRID_PASS_KEY")
    if not client_id or not pass_key:
        raise ValueError("Need EMT_CLIENT_ID and EMT_MADRID_PASS_KEY in Variable Library")
    return client_id, pass_key
