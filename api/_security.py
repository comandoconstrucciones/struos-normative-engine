"""Módulo de seguridad compartido (copia simétrica de vercel-api/api/_security.py)."""
from __future__ import annotations

import os
from collections.abc import Iterable

from fastapi import Header, HTTPException, status

_ILIKE_METACHARS = ("\\", "%", "_", "*", ",")


def ilike_escape(value: str) -> str:
    if not value:
        return ""
    out = value
    for ch in _ILIKE_METACHARS:
        out = out.replace(ch, f"\\{ch}")
    return out


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
    expected = os.environ.get("STRUOS_API_KEY")
    if not expected:
        return
    if not x_api_key or x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-API-Key header",
        )


try:  # pragma: no cover
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    _default_limits = os.environ.get("RATE_LIMIT", "60/minute")
    rate_limiter = Limiter(key_func=get_remote_address, default_limits=[_default_limits])
    SLOWAPI_AVAILABLE = True
except Exception:
    rate_limiter = None  # type: ignore[assignment]
    SLOWAPI_AVAILABLE = False
