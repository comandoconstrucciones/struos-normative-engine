#!/usr/bin/env python3
from dotenv import load_dotenv
load_dotenv()
"""
NSR-10 API Server — FastAPI
Deploy: uvicorn api_server:app --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import json
import requests
from openai import OpenAI

# Config
SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL', 'https://vdakfewjadwaczulcmvj.supabase.co')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
OPENAI_KEY = os.environ.get('OPENAI_API_KEY')

client = OpenAI(api_key=OPENAI_KEY)

HEADERS = {
    'apikey': SERVICE_ROLE,
    'Authorization': f'Bearer {SERVICE_ROLE}',
    'Content-Type': 'application/json'
}

app = FastAPI(
    title="NSR-10 API",
    description="Motor normativo de ingeniería estructural Colombia",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Question(BaseModel):
    query: str
    context_limit: Optional[int] = 5

class SQLQuery(BaseModel):
    table: str
    filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = 100

@app.get("/")
def root():
    return {
        "service": "NSR-10 Normative Engine",
        "version": "1.0.0",
        "endpoints": {
            "/ask": "RAG query (POST)",
            "/sql/{table}": "Direct table query (GET)",
            "/tables": "List all tables (GET)",
            "/search": "FTS search (GET)"
        }
    }

@app.get("/tables")
def list_tables():
    """Lista todas las tablas disponibles"""
    tables = [
        {"name": "nsr10_secciones", "desc": "12,789 secciones FTS", "type": "text"},
        {"name": "nsr10_formulas", "desc": "558 fórmulas", "type": "formulas"},
        {"name": "nsr10_nomenclatura", "desc": "246 símbolos", "type": "symbols"},
        {"name": "nsr10_referencias", "desc": "568 normas externas", "type": "refs"},
        {"name": "nsr10_coef_fa", "desc": "Coef Fa por suelo/Aa", "type": "data"},
        {"name": "nsr10_coef_fv", "desc": "Coef Fv por suelo/Av", "type": "data"},
        {"name": "nsr10_coef_r", "desc": "Coef R, Ω, Cd", "type": "data"},
        {"name": "nsr10_barras_refuerzo", "desc": "Propiedades barras", "type": "data"},
        {"name": "nsr10_cargas_vivas", "desc": "Cargas vivas", "type": "data"},
        {"name": "nsr10_cargas_muertas", "desc": "Cargas muertas", "type": "data"},
        {"name": "nsr10_deriva_max", "desc": "Derivas máximas", "type": "data"},
        {"name": "kg_nodes", "desc": "3,109 nodos KG", "type": "kg"},
        {"name": "kg_edges", "desc": "2,488 edges KG", "type": "kg"},
    ]
    return {"tables": tables, "total": 259}

@app.get("/sql/{table}")
def query_table(table: str, limit: int = 100):
    """Consulta directa a tabla"""
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/{table}",
        params={"select": "*", "limit": limit},
        headers=HEADERS
    )
    if resp.status_code == 404:
        raise HTTPException(404, f"Tabla {table} no existe")
    return resp.json()

@app.get("/search")
def search_fts(q: str, limit: int = 10):
    """Búsqueda full-text en secciones"""
    terms = q.lower().split()
    tsquery = ' & '.join(terms)
    
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/nsr10_secciones",
        params={
            "select": "titulo,seccion,contenido",
            "contenido": f"ilike.*{q}*",
            "limit": limit
        },
        headers=HEADERS
    )
    return {"query": q, "results": resp.json() if resp.ok else []}

@app.post("/ask")
def ask_question(question: Question):
    """RAG: pregunta en lenguaje natural"""
    q = question.query
    
    # 1. Buscar en secciones
    sections = requests.get(
        f"{SUPABASE_URL}/rest/v1/nsr10_secciones",
        params={"contenido": f"ilike.*{q.split()[0]}*", "limit": 3},
        headers=HEADERS
    ).json()
    
    # 2. Buscar tablas relevantes
    tables_data = []
    q_lower = q.lower()
    
    if any(x in q_lower for x in ['fa', 'fv', 'suelo', 'sitio']):
        fa = requests.get(f"{SUPABASE_URL}/rest/v1/nsr10_coef_fa?limit=20", headers=HEADERS).json()
        fv = requests.get(f"{SUPABASE_URL}/rest/v1/nsr10_coef_fv?limit=20", headers=HEADERS).json()
        tables_data.extend([{"tabla": "nsr10_coef_fa", "data": fa}, {"tabla": "nsr10_coef_fv", "data": fv}])
    
    if any(x in q_lower for x in ['barra', 'refuerzo', '#']):
        barras = requests.get(f"{SUPABASE_URL}/rest/v1/nsr10_barras_refuerzo", headers=HEADERS).json()
        tables_data.append({"tabla": "nsr10_barras_refuerzo", "data": barras})
    
    if any(x in q_lower for x in ['deriva', 'desplazamiento']):
        deriva = requests.get(f"{SUPABASE_URL}/rest/v1/nsr10_deriva_max", headers=HEADERS).json()
        tables_data.append({"tabla": "nsr10_deriva_max", "data": deriva})
    
    if any(x in q_lower for x in ['carga viva', 'carga muerta']):
        cv = requests.get(f"{SUPABASE_URL}/rest/v1/nsr10_cargas_vivas?limit=20", headers=HEADERS).json()
        cm = requests.get(f"{SUPABASE_URL}/rest/v1/nsr10_cargas_muertas", headers=HEADERS).json()
        tables_data.extend([{"tabla": "nsr10_cargas_vivas", "data": cv}, {"tabla": "nsr10_cargas_muertas", "data": cm}])
    
    # 3. Construir contexto
    context = []
    if sections:
        context.append("## Secciones NSR-10:")
        for s in sections[:2]:
            context.append(f"**{s.get('seccion','')}**: {s.get('contenido','')[:300]}")
    
    if tables_data:
        context.append("\n## Datos:")
        for t in tables_data:
            context.append(f"**{t['tabla']}**: {json.dumps(t['data'][:5], ensure_ascii=False)}")
    
    # 4. LLM
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un ingeniero estructural experto en NSR-10. Responde técnicamente citando secciones."},
            {"role": "user", "content": f"Contexto:\n{chr(10).join(context)}\n\nPregunta: {q}"}
        ],
        temperature=0.1
    )
    
    return {
        "question": q,
        "answer": response.choices[0].message.content,
        "sources": {"sections": len(sections), "tables": len(tables_data)}
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
