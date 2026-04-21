#!/usr/bin/env python3
"""
NSR-10 API Server — FastAPI
Deploy: uvicorn main:app --host 0.0.0.0 --port 8000
"""
import hashlib
import json
import os
from typing import Any

import requests
from _security import (
    SLOWAPI_AVAILABLE,
    allowed_table,
    allowed_tables,
    get_cors_origins,
    ilike_escape,
    rate_limiter,
    require_api_key,
)
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

# Config
SUPABASE_URL = os.environ.get(
    "STRUOS_SUPABASE_URL", "https://vdakfewjadwaczulcmvj.supabase.co"
)
SERVICE_ROLE = os.environ.get("STRUOS_SUPABASE_SERVICE_ROLE")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

HEADERS = {
    "apikey": SERVICE_ROLE or "",
    "Authorization": f"Bearer {SERVICE_ROLE or ''}",
    "Content-Type": "application/json",
}

app = FastAPI(
    title="NSR-10 API",
    description="Motor normativo de ingeniería estructural Colombia",
    version="1.1.0",
)

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


class Question(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    context_limit: int | None = Field(default=5, ge=1, le=20)


_ASK_CACHE: dict[str, dict[str, Any]] = {}
_ASK_CACHE_MAX = 256


def _cache_key(q: str, ctx_limit: int) -> str:
    return hashlib.sha256(f"{q.strip().lower()}|{ctx_limit}".encode()).hexdigest()


@app.get("/")
def root():
    return {
        "service": "NSR-10 Normative Engine",
        "version": "1.1.0",
        "endpoints": {
            "/ask": "RAG query (POST)",
            "/sql/{table}": "Direct table query (GET) — whitelist aplicada",
            "/tables": "List all tables (GET)",
            "/search": "FTS search (GET)",
        },
    }


@app.get("/tables")
def list_tables():
    """Lista todas las tablas disponibles (whitelist)"""
    tables = list(allowed_tables())
    return {"tables": tables, "total": len(tables)}


@app.get("/sql/{table}", dependencies=[Depends(require_api_key)])
def query_table(table: str, limit: int = Query(default=100, ge=1, le=1000)):
    """Consulta directa a tabla (solo tablas whitelisted)"""
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


@app.get("/search", dependencies=[Depends(require_api_key)])
def search_fts(
    q: str = Query(min_length=2, max_length=120),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Búsqueda full-text en secciones"""
    safe = ilike_escape(q)
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_secciones",
            params={
                "select": "titulo,seccion,contenido",
                "contenido": f"ilike.*{safe}*",
                "limit": limit,
            },
            headers=HEADERS,
            timeout=15,
        )
    except requests.RequestException as e:
        raise HTTPException(502, f"Upstream error: {e}") from e
    return {"query": q, "results": resp.json() if resp.ok else []}


def _build_rag_context(q: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Busca secciones y tablas relevantes para la query.

    Usa todas las palabras significativas (>2 chars) y combina resultados,
    en vez de usar solo la primera palabra como antes.
    """
    stopwords = {
        "el", "la", "los", "las", "de", "del", "en", "un", "una", "y", "o",
        "que", "para", "con", "por", "se", "es", "al", "cual", "cuales",
    }
    terms = [t.lower() for t in q.split() if len(t) > 2 and t.lower() not in stopwords]
    terms = terms[:4]

    sections: list[dict[str, Any]] = []
    seen = set()
    for term in terms or [q]:
        try:
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/nsr10_secciones",
                params={
                    "contenido": f"ilike.*{ilike_escape(term)}*",
                    "select": "titulo,seccion,contenido",
                    "limit": 3,
                },
                headers=HEADERS,
                timeout=10,
            )
            for s in resp.json() or []:
                key = s.get("seccion")
                if key and key not in seen:
                    seen.add(key)
                    sections.append(s)
        except requests.RequestException:
            continue

    q_lower = q.lower()
    tables_data: list[dict[str, Any]] = []

    def fetch(table: str, limit: int = 20):
        try:
            r = requests.get(
                f"{SUPABASE_URL}/rest/v1/{table}?limit={limit}",
                headers=HEADERS,
                timeout=10,
            )
            return r.json() if r.ok else []
        except requests.RequestException:
            return []

    if any(x in q_lower for x in ("fa", "fv", "suelo", "sitio")):
        tables_data.append({"tabla": "nsr10_coef_fa", "data": fetch("nsr10_coef_fa")})
        tables_data.append({"tabla": "nsr10_coef_fv", "data": fetch("nsr10_coef_fv")})

    if any(x in q_lower for x in ("barra", "refuerzo", "#")):
        tables_data.append(
            {"tabla": "nsr10_barras_refuerzo", "data": fetch("nsr10_barras_refuerzo", 50)}
        )

    if any(x in q_lower for x in ("deriva", "desplazamiento")):
        tables_data.append({"tabla": "nsr10_deriva_max", "data": fetch("nsr10_deriva_max", 50)})

    if any(x in q_lower for x in ("carga viva", "carga muerta")):
        tables_data.append({"tabla": "nsr10_cargas_vivas", "data": fetch("nsr10_cargas_vivas")})
        tables_data.append({"tabla": "nsr10_cargas_muertas", "data": fetch("nsr10_cargas_muertas", 50)})

    return sections[:8], tables_data


@app.post("/ask", dependencies=[Depends(require_api_key)])
def ask_question(question: Question):
    """RAG: pregunta en lenguaje natural"""
    if client is None:
        raise HTTPException(503, "OPENAI_API_KEY no configurada")

    q = question.query
    ck = _cache_key(q, question.context_limit or 5)
    cached = _ASK_CACHE.get(ck)
    if cached:
        return {**cached, "cached": True}

    sections, tables_data = _build_rag_context(q)

    context: list[str] = []
    if sections:
        context.append("## Secciones NSR-10:")
        for s in sections[:5]:
            context.append(f"**{s.get('seccion','')}**: {s.get('contenido','')[:300]}")
    if tables_data:
        context.append("\n## Datos:")
        for t in tables_data:
            context.append(
                f"**{t['tabla']}**: {json.dumps(t['data'][:5], ensure_ascii=False)}"
            )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Eres un ingeniero estructural experto en NSR-10. Responde técnicamente citando secciones.",
            },
            {
                "role": "user",
                "content": f"Contexto:\n{chr(10).join(context)}\n\nPregunta: {q}",
            },
        ],
        temperature=0.1,
    )

    result = {
        "question": q,
        "answer": response.choices[0].message.content,
        "sources": {"sections": len(sections), "tables": len(tables_data)},
    }

    if len(_ASK_CACHE) >= _ASK_CACHE_MAX:
        _ASK_CACHE.pop(next(iter(_ASK_CACHE)))
    _ASK_CACHE[ck] = result

    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
