"""
Utilidades de seguridad compartidas por los endpoints.

- ilike_escape: escapa metacaracteres de PostgREST/ILIKE para evitar inyección de patrones.
- allowed_table: whitelist de tablas consultables desde endpoints genéricos.
- get_cors_origins: lee orígenes permitidos desde env ALLOWED_ORIGINS (coma-separados).
- require_api_key: dependencia FastAPI opcional — activa si STRUOS_API_KEY está seteada.
- rate_limiter: SlowAPI limiter (opcional; no-op si slowapi no está instalado).
"""
from __future__ import annotations

import os
from collections.abc import Callable, Iterable

from fastapi import Header, HTTPException, status

# Metacaracteres que PostgREST interpreta en patrones ilike/like.
# `*` es el wildcard de PostgREST; `%` y `_` son wildcards de SQL LIKE;
# `,` separa valores en params.
_ILIKE_METACHARS = ("\\", "%", "_", "*", ",")


def ilike_escape(value: str) -> str:
    """Escapa metacaracteres de un patrón ILIKE/PostgREST para tratar la entrada como literal."""
    if not value:
        return ""
    out = value
    for ch in _ILIKE_METACHARS:
        out = out.replace(ch, f"\\{ch}")
    return out


# Whitelist de tablas consultables desde /sql/{table}.
# Agregar aquí explícitamente cualquier tabla nueva que deba exponerse al público.
_ALLOWED_TABLES: frozenset[str] = frozenset(
    {
        "nsr10_secciones",
        "nsr10_formulas",
        "nsr10_nomenclatura",
        "nsr10_referencias",
        "nsr10_coef_fa",
        "nsr10_coef_fv",
        "nsr10_coef_r",
        "nsr10_barras_refuerzo",
        "nsr10_cargas_vivas",
        "nsr10_cargas_muertas",
        "nsr10_deriva_max",
        "nsr10_municipios",
        "kg_nodes",
        "kg_edges",
    }
)


def allowed_table(name: str) -> bool:
    return name in _ALLOWED_TABLES


def allowed_tables() -> Iterable[str]:
    return sorted(_ALLOWED_TABLES)


def get_cors_origins() -> list[str]:
    """
    Orígenes permitidos por CORS.

    Lee `ALLOWED_ORIGINS` (coma-separados). Si no está definida, usa un default
    conservador con los dominios conocidos del proyecto + localhost para desarrollo.
    Pasar "*" desactiva la restricción (NO recomendado en producción).
    """
    raw = os.environ.get("ALLOWED_ORIGINS", "").strip()
    if not raw:
        return [
            "https://struos-ai.vercel.app",
            "https://struos-api.vercel.app",
            "https://chat.openai.com",
            "https://chatgpt.com",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8000",
        ]
    return [o.strip() for o in raw.split(",") if o.strip()]


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """
    Dependencia FastAPI. Si `STRUOS_API_KEY` está seteada, exige match exacto
    en el header `X-API-Key`. Si no está seteada, no hace nada (modo abierto).

    Uso:
        @app.get("/ask", dependencies=[Depends(require_api_key)])
    """
    expected = os.environ.get("STRUOS_API_KEY")
    if not expected:
        return
    if not x_api_key or x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-API-Key header",
        )


def _identity(func: Callable) -> Callable:  # pragma: no cover
    return func


try:  # pragma: no cover
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    _default_limits = os.environ.get("RATE_LIMIT", "60/minute")
    rate_limiter = Limiter(key_func=get_remote_address, default_limits=[_default_limits])
    SLOWAPI_AVAILABLE = True
except Exception:  # slowapi no instalado → no-op
    rate_limiter = None  # type: ignore[assignment]
    SLOWAPI_AVAILABLE = False
