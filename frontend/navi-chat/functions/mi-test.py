"""
mi-test.py
----------
Test mínimo de ManagedIdentityCredential para scope Fabric.

Uso (local con az login):  python functions/mi-test.py
Uso (Azure VM / App Service con MI): python functions/mi-test.py

Requiere: pip install azure-identity python-dotenv
"""

import os
import json
import sys
from pathlib import Path

from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"


def try_credential(cred, label: str) -> dict:
    try:
        token = cred.get_token(FABRIC_SCOPE)
        return {"success": True, "credential": label, "tokenLength": len(token.token), "expiresOn": token.expires_on}
    except Exception as e:
        return {"success": False, "credential": label, "error": str(e)}


def main():
    results = []

    results.append(try_credential(ManagedIdentityCredential(), "ManagedIdentityCredential"))

    results.append(try_credential(DefaultAzureCredential(), "DefaultAzureCredential"))

    print(json.dumps(results, indent=2))

    any_ok = any(r["success"] for r in results)
    sys.exit(0 if any_ok else 1)


if __name__ == "__main__":
    main()