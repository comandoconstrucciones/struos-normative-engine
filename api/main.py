#!/usr/bin/env python3
"""
NSR-10 API — Railway entrypoint.

Re-exporta la app de `vercel-api/api/index.py` para evitar duplicación.
Si alguien quiere ejecutar este módulo directamente:

    uvicorn main:app --host 0.0.0.0 --port 8000

...Railway usa `Procfile` que apunta a este archivo.
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Insertar vercel-api/api en sys.path para reusar el módulo canónico.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "vercel-api" / "api"))

from index import app  # noqa: E402, F401  — re-export para uvicorn

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
