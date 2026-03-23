#!/usr/bin/env python3
"""
Pipeline de búsqueda avanzada: Híbrido + Reranking
"""
import os, requests, re
from openai import OpenAI

SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
HEADERS = {'apikey': SERVICE_ROLE, 'Authorization': f'Bearer {SERVICE_ROLE}', 'Content-Type': 'application/json'}

client = OpenAI()

# =====================================================
# PASO 1: QUERY TRANSFORMATION
# =====================================================
def transform_query(query: str) -> list[str]:
    """Expande el query con sinónimos del dominio NSR-10"""
    queries = [query]
    
    # Sinónimos del dominio
    synonyms = {
        'deriva': ['drift', 'desplazamiento relativo', 'desplazamiento entrepiso'],
        'cortante': ['shear', 'fuerza cortante', 'corte basal'],
        'período': ['periodo', 'frecuencia natural'],
        'pórtico': ['portico', 'marco', 'frame'],
        'mampostería': ['mamposteria', 'muros de ladrillo'],
    }
    
    query_lower = query.lower()
    for term, syns in synonyms.items():
        if term in query_lower:
            for syn in syns[:1]:  # Solo 1 sinónimo para no explotar
                queries.append(query_lower.replace(term, syn))
    
    # Extraer referencias a tablas/secciones
    tables = re.findall(r'[Tt]abla\s*(A[\.\-]?\d+[\.\-\d]*)', query)
    sections = re.findall(r'[Ss]ecci[oó]n\s*(A[\.\-]?\d+[\.\-\d]*)', query)
    refs = re.findall(r'(A\.\d+\.\d+[\.\-\d]*)', query)
    
    for ref in tables + sections + refs:
        queries.append(ref)
    
    return list(set(queries))[:3]  # Max 3 queries

# =====================================================
# PASO 2: BÚSQUEDA HÍBRIDA (BM25 + Vector)
# =====================================================
def hybrid_search(query: str, limit: int = 30):
    """Búsqueda híbrida con RRF fusion"""
    response = client.embeddings.create(model="text-embedding-3-small", input=query)
    embedding = response.data[0].embedding
    
    url = f"{SUPABASE_URL}/rest/v1/rpc/hybrid_search"
    payload = {
        "query_text": query,
        "query_embedding": embedding,
        "match_count": limit,
        "bm25_weight": 0.4,
        "vector_weight": 0.6
    }
    
    r = requests.post(url, headers=HEADERS, json=payload)
    results = r.json()
    return results if isinstance(results, list) else []

# =====================================================
# PASO 3: RERANKING (simple por ahora)
# =====================================================
def rerank(query: str, documents: list, top_k: int = 10) -> list:
    """Rerank basado en coincidencia de términos"""
    query_terms = set(re.findall(r'\w+', query.lower()))
    query_terms -= {'el', 'la', 'de', 'en', 'para', 'que', 'es', 'un', 'una', 'los', 'las', 'del', 'al'}
    
    scored = []
    for doc in documents:
        content = f"{doc.get('title', '')} {doc.get('content', '')}".lower()
        
        # Score basado en términos encontrados
        matches = sum(1 for term in query_terms if term in content)
        term_score = matches / len(query_terms) if query_terms else 0
        
        # Bonus por coincidencia exacta de sección
        section = doc.get('section_path', '').lower()
        section_bonus = 0.3 if any(term in section for term in query_terms) else 0
        
        # Score híbrido original
        hybrid_score = doc.get('hybrid_score', 0) or 0
        
        # Score final
        final_score = (0.4 * hybrid_score * 100) + (0.4 * term_score) + (0.2 * section_bonus)
        
        doc_copy = doc.copy()
        doc_copy['final_score'] = final_score
        scored.append(doc_copy)
    
    scored.sort(key=lambda x: x['final_score'], reverse=True)
    return scored[:top_k]

# =====================================================
# PIPELINE COMPLETO
# =====================================================
def advanced_search(query: str, top_k: int = 5) -> list:
    """
    Pipeline completo:
    1. Query transformation
    2. Multi-query hybrid search
    3. Deduplication
    4. Reranking
    """
    # 1. Transform query
    queries = transform_query(query)
    
    # 2. Multi-query search
    all_results = {}
    for q in queries:
        results = hybrid_search(q, limit=20)
        for r in results:
            rid = r.get('id', '')
            if rid not in all_results:
                all_results[rid] = r
            else:
                # Combinar scores
                existing_score = all_results[rid].get('hybrid_score', 0) or 0
                new_score = r.get('hybrid_score', 0) or 0
                all_results[rid]['hybrid_score'] = max(existing_score, new_score)
    
    # 3. Deduplicate
    candidates = list(all_results.values())
    
    # 4. Rerank
    final = rerank(query, candidates, top_k=top_k)
    
    return final

# =====================================================
# TEST
# =====================================================
if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║              BÚSQUEDA AVANZADA: HÍBRIDO + RERANKING                          ║")
    print("╠══════════════════════════════════════════════════════════════════════════════╣")
    print()
    
    test_queries = [
        "¿Cuál es la deriva máxima permitida para concreto?",
        "Tabla A.2.4-3 coeficiente Fa",
        "valores de R0 para pórtico especial",
        "zona sísmica de Bogotá",
        "espectro de aceleraciones de diseño",
    ]
    
    for query in test_queries:
        print(f"🔍 {query}")
        results = advanced_search(query, top_k=3)
        
        for i, r in enumerate(results, 1):
            section = r.get('section_path', '')[:25]
            title = (r.get('title', '') or '')[:35]
            score = r.get('final_score', 0)
            print(f"   {i}. [{score:.2f}] {section} — {title}")
        print()
    
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
