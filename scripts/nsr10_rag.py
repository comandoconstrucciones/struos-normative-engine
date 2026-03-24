#!/usr/bin/env python3
"""
NSR-10 RAG API — Búsqueda semántica + SQL
Endpoint para consultas de ingeniería estructural
"""
import os
import json
import requests
from typing import Optional, List, Dict, Any
from openai import OpenAI

# Config
SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
OPENAI_KEY = os.environ.get('OPENAI_API_KEY')

client = OpenAI(api_key=OPENAI_KEY)

HEADERS = {
    'apikey': SERVICE_ROLE,
    'Authorization': f'Bearer {SERVICE_ROLE}',
    'Content-Type': 'application/json'
}

def get_embedding(text: str) -> List[float]:
    """Genera embedding usando OpenAI"""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def search_fts(query: str, limit: int = 10) -> List[Dict]:
    """Búsqueda full-text en secciones"""
    # Convertir query a tsquery
    terms = query.lower().split()
    tsquery = ' & '.join(terms)
    
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/nsr10_secciones",
        params={
            "select": "titulo,seccion,contenido",
            "search_vector": f"fts.{tsquery}",
            "limit": limit
        },
        headers=HEADERS
    )
    return resp.json() if resp.ok else []

def search_tables(query: str) -> List[Dict]:
    """Busca en tablas de datos específicos"""
    results = []
    
    # Detectar qué busca
    query_lower = query.lower()
    
    # Barras de refuerzo
    if any(x in query_lower for x in ['barra', 'refuerzo', 'acero', '#', 'no.']):
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_barras_refuerzo",
            params={"select": "*"},
            headers=HEADERS
        )
        if resp.ok:
            results.append({"tabla": "nsr10_barras_refuerzo", "data": resp.json()})
    
    # Coeficientes sísmicos
    if any(x in query_lower for x in ['fa', 'fv', 'sismo', 'suelo', 'sitio']):
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_coef_fa",
            params={"select": "*"},
            headers=HEADERS
        )
        if resp.ok:
            results.append({"tabla": "nsr10_coef_fa", "data": resp.json()})
        
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_coef_fv",
            params={"select": "*"},
            headers=HEADERS
        )
        if resp.ok:
            results.append({"tabla": "nsr10_coef_fv", "data": resp.json()})
    
    # R, Cd
    if any(x in query_lower for x in ['coef r', 'disipación', 'cd', 'omega']):
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_coef_r",
            params={"select": "*"},
            headers=HEADERS
        )
        if resp.ok:
            results.append({"tabla": "nsr10_coef_r", "data": resp.json()})
    
    # Cargas
    if any(x in query_lower for x in ['carga viva', 'carga muerta', 'peso']):
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_cargas_vivas",
            params={"select": "*"},
            headers=HEADERS
        )
        if resp.ok:
            results.append({"tabla": "nsr10_cargas_vivas", "data": resp.json()})
        
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/nsr10_cargas_muertas",
            params={"select": "*"},
            headers=HEADERS
        )
        if resp.ok:
            results.append({"tabla": "nsr10_cargas_muertas", "data": resp.json()})
    
    return results

def search_formulas(query: str, limit: int = 5) -> List[Dict]:
    """Busca fórmulas relevantes"""
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/nsr10_formulas",
        params={
            "select": "nombre,simbolo,seccion,descripcion,formula_latex,codigo_python",
            "or": f"(nombre.ilike.*{query}*,descripcion.ilike.*{query}*)",
            "limit": limit
        },
        headers=HEADERS
    )
    return resp.json() if resp.ok else []

def search_nomenclatura(simbolo: str) -> Optional[Dict]:
    """Busca definición de un símbolo"""
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/nsr10_nomenclatura",
        params={
            "select": "*",
            "simbolo": f"eq.{simbolo}"
        },
        headers=HEADERS
    )
    data = resp.json() if resp.ok else []
    return data[0] if data else None

def rag_query(question: str) -> Dict[str, Any]:
    """
    RAG completo: busca contexto relevante y genera respuesta
    """
    # 1. Búsqueda FTS en secciones
    fts_results = search_fts(question, limit=5)
    
    # 2. Búsqueda en tablas de datos
    table_results = search_tables(question)
    
    # 3. Búsqueda de fórmulas
    formula_results = search_formulas(question, limit=3)
    
    # 4. Construir contexto
    context_parts = []
    
    if fts_results:
        context_parts.append("## Secciones NSR-10 relevantes:")
        for s in fts_results[:3]:
            context_parts.append(f"**{s.get('seccion', '')}** ({s.get('titulo', '')})")
            context_parts.append(s.get('contenido', '')[:500])
    
    if table_results:
        context_parts.append("\n## Datos de tablas:")
        for t in table_results:
            context_parts.append(f"**{t['tabla']}**")
            context_parts.append(json.dumps(t['data'][:5], indent=2, ensure_ascii=False))
    
    if formula_results:
        context_parts.append("\n## Fórmulas:")
        for f in formula_results:
            context_parts.append(f"**{f.get('nombre', '')}** ({f.get('seccion', '')})")
            if f.get('formula_latex'):
                context_parts.append(f"  LaTeX: {f['formula_latex']}")
    
    context = "\n".join(context_parts)
    
    # 5. Generar respuesta con LLM
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """Eres un ingeniero estructural experto en la NSR-10 de Colombia.
Responde preguntas técnicas basándote en el contexto proporcionado.
Siempre cita la sección de la norma cuando sea posible.
Si hay tablas de datos, úsalas para dar valores específicos.
Responde en español técnico."""
            },
            {
                "role": "user",
                "content": f"""Contexto NSR-10:
{context}

Pregunta: {question}"""
            }
        ],
        temperature=0.1
    )
    
    return {
        "question": question,
        "answer": response.choices[0].message.content,
        "sources": {
            "sections": len(fts_results),
            "tables": len(table_results),
            "formulas": len(formula_results)
        },
        "context_preview": context[:1000]
    }

# CLI
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python3 nsr10_rag.py 'pregunta'")
        print("Ejemplo: python3 nsr10_rag.py '¿Cuál es el área de una barra #5?'")
        sys.exit(1)
    
    question = " ".join(sys.argv[1:])
    result = rag_query(question)
    
    print("=" * 60)
    print(f"Pregunta: {result['question']}")
    print("=" * 60)
    print(f"\n{result['answer']}")
    print("\n" + "=" * 60)
    print(f"Fuentes: {result['sources']}")
