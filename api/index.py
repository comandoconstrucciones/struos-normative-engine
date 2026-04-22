#!/usr/bin/env python3
"""
NSR-10 API Server — FastAPI for Vercel Serverless (single-file Lambda).

Todo el código de seguridad está inlineado abajo porque Vercel Python
empaca solo el archivo entrypoint — imports desde `_security.py` vecino
fallan con ImportError en runtime.
"""
import hashlib
import os
import unicodedata
from collections.abc import Iterable
from typing import Any

import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# =============================================================================
# Security utilities (inline)
# =============================================================================

_ILIKE_METACHARS = ("\\", "%", "_", "*", ",")


def ilike_escape(value: str) -> str:
    """Escapa metacaracteres de PostgREST/ILIKE para tratar la entrada como literal."""
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
    """
    Orígenes permitidos por CORS. Lee `ALLOWED_ORIGINS` (coma-separados).
    Si no está definida, usa un default con los dominios del proyecto + localhost.
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
    """Exige X-API-Key si `STRUOS_API_KEY` está seteada; si no, abierto."""
    expected = os.environ.get("STRUOS_API_KEY")
    if not expected:
        return
    if not x_api_key or x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-API-Key header",
        )


try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    _default_limits = os.environ.get("RATE_LIMIT", "60/minute")
    rate_limiter = Limiter(key_func=get_remote_address, default_limits=[_default_limits])
    SLOWAPI_AVAILABLE = True
except Exception:
    rate_limiter = None  # type: ignore[assignment]
    SLOWAPI_AVAILABLE = False

# Config
SUPABASE_URL = os.environ.get(
    "STRUOS_SUPABASE_URL", "https://vdakfewjadwaczulcmvj.supabase.co"
)
SERVICE_ROLE = os.environ.get("STRUOS_SUPABASE_SERVICE_ROLE", "")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

HEADERS = {
    "apikey": SERVICE_ROLE,
    "Authorization": f"Bearer {SERVICE_ROLE}",
    "Content-Type": "application/json",
}

# OpenAI lazy-init (opcional — /ask responde 503 si no hay key)
try:
    from openai import OpenAI

    _openai_client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None
except ImportError:
    _openai_client = None

app = FastAPI(title="NSR-10 API", version="1.3.0")

if SLOWAPI_AVAILABLE:
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    app.state.limiter = rate_limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(request, exc):  # pragma: no cover
        return HTTPException(status_code=429, detail="Rate limit exceeded")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)

# === UTILIDADES ===

def normalize_text(text: str) -> str:
    """Quita acentos para búsqueda flexible"""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def search_municipio(nombre: str):
    """Busca municipio con y sin acentos (entrada tratada como literal)"""
    safe = ilike_escape(nombre)
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/nsr10_municipios",
        params={
            "municipio": f"ilike.*{safe}*",
            "select": "municipio,departamento,aa,av,zona_amenaza",
        },
        headers=HEADERS,
        timeout=10,
    )
    data = resp.json()

    if data and isinstance(data, list) and len(data) > 0:
        return data

    ACCENT_MAP = {
        "a": ["á", "à", "ä"],
        "e": ["é", "è", "ë"],
        "i": ["í", "ì", "ï"],
        "o": ["ó", "ò", "ö"],
        "u": ["ú", "ù", "ü"],
        "n": ["ñ"],
    }

    nombre_lower = nombre.lower()
    variantes = []
    for base, accented_list in ACCENT_MAP.items():
        if base in nombre_lower:
            for accented in accented_list:
                variantes.append(nombre_lower.replace(base, accented).title())

    for variante in variantes:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_municipios",
            params={
                "municipio": f"ilike.*{ilike_escape(variante)}*",
                "select": "municipio,departamento,aa,av,zona_amenaza",
            },
            headers=HEADERS,
            timeout=10,
        )
        data = resp.json()
        if data and isinstance(data, list) and len(data) > 0:
            return data

    # Fallback: traer todos y filtrar en Python
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/nsr10_municipios",
        params={"select": "municipio,departamento,aa,av,zona_amenaza", "limit": "1200"},
        headers=HEADERS,
        timeout=15,
    )
    all_municipios = resp.json()
    if isinstance(all_municipios, list):
        nombre_norm = normalize_text(nombre).lower()
        matches = [
            m
            for m in all_municipios
            if nombre_norm in normalize_text(m.get("municipio", "")).lower()
        ]
        if matches:
            return matches
    return []


# === ENDPOINTS ===

@app.get("/")
def root():
    return {
        "service": "NSR-10 Normative Engine",
        "version": "1.3.0",
        "status": "ok",
        "endpoints": [
            "/municipios/{nombre}",
            "/coef/fa/{suelo}/{aa}",
            "/coef/fv/{suelo}/{av}",
            "/barras",
            "/deriva",
            "/coef/r",
            "/search",
            "/ask",
            "/ask/folders",
            "/tables",
            "/sql/{table}",
        ],
    }


@app.get("/municipios/{nombre}", dependencies=[Depends(require_api_key)])
def get_municipio(nombre: str):
    """Busca municipio - funciona con o sin acentos"""
    if not nombre or len(nombre) > 80:
        raise HTTPException(400, "nombre inválido (1-80 chars)")
    try:
        return search_municipio(nombre)
    except requests.RequestException as e:
        raise HTTPException(502, f"Upstream error: {e}") from e


_VALID_SOIL = {"A", "B", "C", "D", "E", "F"}
_VALID_AA_AV = {0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50}


@app.get("/coef/fa/{suelo}/{aa}", dependencies=[Depends(require_api_key)])
def get_fa(suelo: str, aa: float):
    """Coeficiente Fa por tipo de suelo y Aa"""
    suelo_upper = suelo.upper()
    if suelo_upper not in _VALID_SOIL:
        raise HTTPException(400, "suelo debe ser A-F")
    if aa not in _VALID_AA_AV:
        raise HTTPException(400, "aa inválido. Valores: 0.05..0.50 en pasos de 0.05")

    if suelo_upper == "F":
        return {
            "suelo": "F",
            "aa": aa,
            "fa": None,
            "nota": "Suelo tipo F requiere estudio de sitio específico (NSR-10 A.2.4.4)",
            "referencia": "NSR-10 Tabla A.2.4-3",
        }
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_coef_fa",
            params={
                "soil_type": f"eq.{suelo_upper}",
                "aa_value": f"eq.{aa}",
                "select": "fa",
            },
            headers=HEADERS,
            timeout=10,
        )
        data = resp.json()
    except requests.RequestException as e:
        raise HTTPException(502, f"Upstream error: {e}") from e
    if not data or isinstance(data, dict):
        return {"suelo": suelo, "aa": aa, "fa": None, "error": "Valor no encontrado"}
    return {"suelo": suelo, "aa": aa, "fa": data[0]["fa"], "referencia": "NSR-10 Tabla A.2.4-3"}


@app.get("/coef/fv/{suelo}/{av}", dependencies=[Depends(require_api_key)])
def get_fv(suelo: str, av: float):
    """Coeficiente Fv por tipo de suelo y Av"""
    suelo_upper = suelo.upper()
    if suelo_upper not in _VALID_SOIL:
        raise HTTPException(400, "suelo debe ser A-F")
    if av not in _VALID_AA_AV:
        raise HTTPException(400, "av inválido. Valores: 0.05..0.50 en pasos de 0.05")

    if suelo_upper == "F":
        return {
            "suelo": "F",
            "av": av,
            "fv": None,
            "nota": "Suelo tipo F requiere estudio de sitio específico (NSR-10 A.2.4.4)",
            "referencia": "NSR-10 Tabla A.2.4-4",
        }
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_coef_fv",
            params={
                "soil_type": f"eq.{suelo_upper}",
                "av_value": f"eq.{av}",
                "select": "fv",
            },
            headers=HEADERS,
            timeout=10,
        )
        data = resp.json()
    except requests.RequestException as e:
        raise HTTPException(502, f"Upstream error: {e}") from e
    if not data or isinstance(data, dict):
        return {"suelo": suelo, "av": av, "fv": None, "error": "Valor no encontrado"}
    return {"suelo": suelo, "av": av, "fv": data[0]["fv"], "referencia": "NSR-10 Tabla A.2.4-4"}


@app.get("/barras", dependencies=[Depends(require_api_key)])
def get_barras(designacion: str | None = Query(default=None, max_length=16)):
    """Barras de refuerzo - propiedades"""
    try:
        params = {
            "select": "designacion,diametro_mm,area_mm2,masa_kg_m",
            "limit": "30",
            "order": "diametro_mm",
        }
        if designacion:
            params["designacion"] = f"ilike.*{ilike_escape(designacion)}*"
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_barras_refuerzo",
            params=params,
            headers=HEADERS,
            timeout=10,
        )
        return {"barras": resp.json(), "referencia": "NSR-10 Tabla C.3.5.3-1"}
    except requests.RequestException as e:
        raise HTTPException(502, f"Upstream error: {e}") from e


@app.get("/deriva", dependencies=[Depends(require_api_key)])
def get_deriva():
    """Derivas máximas permitidas por sistema estructural"""
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_deriva_max",
            params={"select": "*"},
            headers=HEADERS,
            timeout=10,
        )
        return {"derivas": resp.json(), "referencia": "NSR-10 Tabla A.6.4-1"}
    except requests.RequestException as e:
        raise HTTPException(502, f"Upstream error: {e}") from e


_VALID_CAPACIDAD = {"DES", "DMO", "DMI"}


@app.get("/coef/r", dependencies=[Depends(require_api_key)])
def get_coef_r(
    sistema: str | None = Query(default=None, max_length=80),
    capacidad: str | None = Query(default=None, max_length=3),
):
    """Coeficientes R₀, Ω₀, Cd por sistema estructural"""
    try:
        params = {"select": "sistema,capacidad_disipacion,r0,omega0,cd", "limit": "30"}
        if capacidad:
            cap = capacidad.upper()
            if cap not in _VALID_CAPACIDAD:
                raise HTTPException(400, "capacidad debe ser DES, DMO o DMI")
            params["capacidad_disipacion"] = f"eq.{cap}"

        if sistema:
            params["sistema"] = f"ilike.*{ilike_escape(sistema)}*"
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/nsr10_coef_r",
                params=params,
                headers=HEADERS,
                timeout=10,
            )
            data = resp.json()

            if not data or (isinstance(data, list) and len(data) == 0):
                del params["sistema"]
                resp = requests.get(
                    f"{SUPABASE_URL}/rest/v1/nsr10_coef_r",
                    params=params,
                    headers=HEADERS,
                    timeout=10,
                )
                all_data = resp.json()
                if isinstance(all_data, list):
                    sistema_norm = normalize_text(sistema).lower()
                    data = [
                        s
                        for s in all_data
                        if sistema_norm in normalize_text(s.get("sistema", "")).lower()
                    ]
        else:
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/nsr10_coef_r",
                params=params,
                headers=HEADERS,
                timeout=10,
            )
            data = resp.json()

        return {"sistemas": data, "referencia": "NSR-10 Tabla A.3-3"}
    except requests.RequestException as e:
        raise HTTPException(502, f"Upstream error: {e}") from e


@app.get("/search", dependencies=[Depends(require_api_key)])
def search_fts(
    q: str = Query(min_length=2, max_length=120),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Búsqueda Full-Text en secciones de la NSR-10 (12,789 secciones indexadas)"""
    try:
        SYNONYMS = {
            "basal": "base",
            "basales": "base",
            "sismico": "sísmico",
            "sismica": "sísmica",
            "calculo": "cálculo",
            "diseno": "diseño",
            "seccion": "sección",
            "armado": "reforzado",
        }
        terms = q.strip().lower().split()
        terms = [SYNONYMS.get(t, t) for t in terms]
        # Sanitizar términos FTS: solo letras/dígitos/acentos (to_tsquery rechaza otros)
        import re

        safe_terms = [re.sub(r"[^\w\sáéíóúñü-]", "", t, flags=re.UNICODE) for t in terms]
        safe_terms = [t for t in safe_terms if t]
        if not safe_terms:
            raise HTTPException(400, "query sin términos válidos")
        fts_query = " & ".join(safe_terms) if len(safe_terms) > 1 else safe_terms[0]

        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_secciones",
            params={
                "search_vector": f"fts(simple).{fts_query}",
                "select": "seccion,titulo,contenido",
                "limit": str(limit),
                "order": "seccion",
            },
            headers=HEADERS,
            timeout=15,
        )
        results = resp.json()
        method = "fts"

        if not results or (isinstance(results, list) and len(results) == 0):
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/nsr10_secciones",
                params={
                    "contenido": f"ilike.*{ilike_escape(q)}*",
                    "select": "seccion,titulo,contenido",
                    "limit": str(limit),
                },
                headers=HEADERS,
                timeout=15,
            )
            results = resp.json()
            method = "ilike"

        if isinstance(results, list):
            for r in results:
                if r.get("contenido") and len(r["contenido"]) > 300:
                    r["contenido"] = r["contenido"][:300] + "..."

        return {
            "query": q,
            "method": method,
            "count": len(results) if isinstance(results, list) else 0,
            "results": results,
        }
    except requests.RequestException as e:
        raise HTTPException(502, f"Upstream error: {e}") from e


# === /ask — RAG vectorial sobre rag_chunks (pgvector 1536) ===

class Question(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    context_limit: int | None = Field(default=8, ge=1, le=20)
    folder: str | None = Field(default="NSR-10", max_length=40)


_ASK_CACHE: dict[str, dict[str, Any]] = {}
_ASK_CACHE_MAX = 256


def _cache_key(q: str, ctx_limit: int) -> str:
    return hashlib.sha256(f"{q.strip().lower()}|{ctx_limit}".encode()).hexdigest()


def _embed_query(text: str) -> list[float]:
    if _openai_client is None:
        raise HTTPException(503, "OPENAI_API_KEY no configurada")
    resp = _openai_client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return resp.data[0].embedding


def _rag_vector_search(
    q_embedding: list[float], match_count: int = 8, folder: str | None = "NSR-10"
) -> list[dict[str, Any]]:
    try:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/match_rag_chunks",
            headers=HEADERS,
            json={
                "query_embedding": q_embedding,
                "match_count": match_count,
                "folder_filter": folder,
            },
            timeout=15,
        )
    except requests.RequestException as e:
        raise HTTPException(502, f"Upstream error (vector search): {e}") from e
    if not resp.ok:
        raise HTTPException(502, f"match_rag_chunks failed: {resp.status_code}")
    return resp.json() or []


@app.post("/ask", dependencies=[Depends(require_api_key)])
def ask_question(question: Question):
    """RAG vectorial: embedding → match_rag_chunks → LLM con citas."""
    if _openai_client is None:
        raise HTTPException(503, "OPENAI_API_KEY no configurada")

    q = question.query
    folder = question.folder or None
    limit = question.context_limit or 8

    ck = _cache_key(f"{q}|{folder}", limit)
    cached = _ASK_CACHE.get(ck)
    if cached:
        return {**cached, "cached": True}

    q_emb = _embed_query(q)
    chunks = _rag_vector_search(q_emb, match_count=limit, folder=folder)

    if not chunks:
        return {
            "question": q,
            "answer": "No encontré fragmentos relevantes en la base. Intenta reformular o ampliar el `folder`.",
            "sources": [],
            "folder": folder,
        }

    context_lines = []
    for i, c in enumerate(chunks, 1):
        sim = c.get("similarity", 0)
        context_lines.append(
            f"[{i}] ({c.get('filename','?')} p.{c.get('page','?')}, sim={sim:.3f})\n"
            f"{c.get('chunk_text','')}"
        )

    response = _openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un ingeniero estructural experto en la NSR-10 colombiana. "
                    "Responde en español, técnicamente, citando fragmentos como [1], [2]. "
                    "Si el contexto no contiene la respuesta, dilo explícitamente — "
                    "no inventes secciones, fórmulas ni tablas."
                ),
            },
            {
                "role": "user",
                "content": f"Contexto:\n{chr(10).join(context_lines)}\n\nPregunta: {q}",
            },
        ],
        temperature=0.1,
    )

    result = {
        "question": q,
        "answer": response.choices[0].message.content,
        "folder": folder,
        "sources": [
            {
                "n": i,
                "filename": c.get("filename"),
                "page": c.get("page"),
                "similarity": round(c.get("similarity", 0), 4),
                "excerpt": (c.get("chunk_text") or "")[:160] + "...",
            }
            for i, c in enumerate(chunks, 1)
        ],
    }

    if len(_ASK_CACHE) >= _ASK_CACHE_MAX:
        _ASK_CACHE.pop(next(iter(_ASK_CACHE)))
    _ASK_CACHE[ck] = result

    return result


@app.get("/tables")
def list_tables_endpoint():
    """Lista las tablas consultables desde /sql/{table} (whitelist)."""
    tables = list(allowed_tables())
    return {"tables": tables, "total": len(tables)}


@app.get("/sql/{table}", dependencies=[Depends(require_api_key)])
def query_table(table: str, limit: int = Query(default=100, ge=1, le=1000)):
    """Consulta directa a una tabla (solo tablas en la whitelist)."""
    if not allowed_table(table):
        raise HTTPException(
            403, f"Tabla '{table}' no expuesta. Ver /tables para la lista permitida."
        )
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}",
            params={"select": "*", "limit": limit},
            headers=HEADERS,
            timeout=15,
        )
    except requests.RequestException as e:
        raise HTTPException(502, f"Upstream error: {e}") from e
    if resp.status_code == 404:
        raise HTTPException(404, f"Tabla {table} no existe")
    return resp.json()


@app.get("/ask/folders")
def list_ask_folders():
    """Folders disponibles para filtrar en /ask."""
    return {
        "folders": [
            "NSR-10",
            "AISC Design Guides",
            "Catálogos",
            "Manuales",
            "Normas técnicas",
        ],
        "default": "NSR-10",
    }


@app.get("/health")
def health():
    """Health check"""
    return {"status": "healthy", "version": "1.3.0"}
