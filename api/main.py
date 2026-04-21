#!/usr/bin/env python3
"""
NSR-10 API Server — FastAPI
Deploy: uvicorn main:app --host 0.0.0.0 --port 8000
"""
import hashlib
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


EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMS = 1536  # debe coincidir con rag_chunks.embedding (vector(1536))


class Question(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    context_limit: int | None = Field(default=8, ge=1, le=20)
    folder: str | None = Field(default="NSR-10", max_length=40)


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


def _embed_query(text: str) -> list[float]:
    """Genera embedding OpenAI de 1536 dims para la query."""
    if client is None:
        raise HTTPException(503, "OPENAI_API_KEY no configurada")
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return resp.data[0].embedding


def _rag_chunks_vector_search(
    q_embedding: list[float],
    match_count: int = 8,
    folder: str | None = "NSR-10",
) -> list[dict[str, Any]]:
    """Llama a la función SQL match_rag_chunks via PostgREST RPC.

    Retorna chunks ordenados por similaridad coseno descendente.
    """
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
        raise HTTPException(502, f"match_rag_chunks failed: {resp.status_code} {resp.text[:200]}")
    return resp.json() or []


def _related_kg_nodes(chunk_ids: list[int], max_rel: int = 5) -> list[dict[str, Any]]:
    """Dados los chunks recuperados, busca nodos KG relacionados por palabras clave
    en el label (aproximación ligera sin JOIN directo chunk↔KG).

    Retorna SECCIONES/FÓRMULAS del KG para enriquecer la respuesta.
    """
    # Implementación simple: por ahora el KG no tiene link directo a rag_chunks,
    # así que no intentamos JOIN. Placeholder para una v2 con chunk.kg_node_id.
    return []


def _build_rag_context(q: str, limit: int, folder: str | None) -> dict[str, Any]:
    """RAG vectorial: embedding + pgvector cosine search + formateo."""
    q_embedding = _embed_query(q)
    chunks = _rag_chunks_vector_search(q_embedding, match_count=limit, folder=folder)
    return {
        "chunks": chunks,
        "folder": folder,
    }


@app.post("/ask", dependencies=[Depends(require_api_key)])
def ask_question(question: Question):
    """RAG vectorial sobre la NSR-10 (y otras normas indexadas).

    Pipeline:
      1. embedding(query) con OpenAI text-embedding-3-small (1536 dims).
      2. match_rag_chunks() en Supabase → top-k chunks por coseno.
      3. LLM responde citando los chunks.

    Parámetros:
      - query: pregunta en lenguaje natural (3-500 chars).
      - context_limit: número de chunks a recuperar (1-20, default 8).
      - folder: uno de ["NSR-10", "AISC Design Guides", "Catálogos",
                        "Manuales", "Normas técnicas"]. Default "NSR-10".
        Pasar null para buscar en todas las normas.
    """
    if client is None:
        raise HTTPException(503, "OPENAI_API_KEY no configurada")

    q = question.query
    folder = question.folder or None
    limit = question.context_limit or 8

    ck = _cache_key(f"{q}|{folder}", limit)
    cached = _ASK_CACHE.get(ck)
    if cached:
        return {**cached, "cached": True}

    ctx = _build_rag_context(q, limit=limit, folder=folder)
    chunks = ctx["chunks"]

    if not chunks:
        return {
            "question": q,
            "answer": "No encontré fragmentos relevantes en la base. Intenta reformular o ampliar el `folder`.",
            "sources": [],
            "folder": folder,
        }

    # Formatear contexto con citas trazables
    context_lines = []
    for i, c in enumerate(chunks, 1):
        sim = c.get("similarity", 0)
        context_lines.append(
            f"[{i}] ({c.get('filename','?')} p.{c.get('page','?')}, sim={sim:.3f})\n"
            f"{c.get('chunk_text','')}"
        )
    context_block = "\n\n".join(context_lines)

    response = client.chat.completions.create(
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
                "content": f"Contexto:\n{context_block}\n\nPregunta: {q}",
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


@app.get("/ask/folders", dependencies=[Depends(require_api_key)])
def list_ask_folders():
    """Lista los folders disponibles para filtrar en /ask."""
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
