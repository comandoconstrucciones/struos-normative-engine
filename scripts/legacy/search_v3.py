#!/usr/bin/env python3
"""
Búsqueda final v3 - con fallback a búsqueda exacta
"""
import os, requests, re
from openai import OpenAI

SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
HEADERS = {'apikey': SERVICE_ROLE, 'Authorization': f'Bearer {SERVICE_ROLE}', 'Content-Type': 'application/json'}

client = OpenAI()

NSR10_SYNONYMS = {
    'cortante basal': ['cortante sísmico en la base', 'Vs'],
    'deriva': ['drift', 'desplazamiento relativo'],
    'deriva máxima': ['límite de deriva', 'deriva máxima permisible'],
    'pórtico especial': ['DES', 'capacidad especial'],
    'zona sísmica': ['amenaza sísmica'],
}

def extract_exact_refs(query: str) -> list[str]:
    """Extrae referencias exactas como 'Tabla A.2.4-3'"""
    refs = []
    # Tabla A.X.X-X
    refs.extend(re.findall(r'[Tt]abla\s*(A[\.\-]?\d+[\.\-]?\d*[\-]?\d*)', query))
    # Sección A.X.X
    refs.extend(re.findall(r'[Ss]ecci[oó]n\s*(A[\.\-]?\d+[\.\-]?\d*)', query))
    # A.X.X directo
    refs.extend(re.findall(r'\b(A\.\d+(?:\.\d+)*(?:-\d+)?)\b', query))
    return refs

def search_exact(ref: str) -> list[dict]:
    """Búsqueda exacta por section_path"""
    # Normalizar referencia
    ref_normalized = ref.replace('.', '.').strip()
    
    # Buscar como Tabla o directo
    patterns = [
        f"Tabla {ref_normalized}",
        f"Tabla {ref_normalized.replace('.', '-')}",
        ref_normalized,
        ref_normalized.replace('-', '.'),
    ]
    
    for pattern in patterns:
        url = f"{SUPABASE_URL}/rest/v1/kg_nodes?section_path=ilike.*{pattern}*&limit=5"
        url = url.replace(' ', '%20')
        r = requests.get(url, headers=HEADERS)
        if r.status_code == 200:
            results = r.json()
            if results:
                return results
    
    return []

def expand_query(query: str) -> list[str]:
    queries = [query]
    query_lower = query.lower()
    
    for term, synonyms in NSR10_SYNONYMS.items():
        if term in query_lower:
            for syn in synonyms[:1]:
                expanded = query_lower.replace(term, syn)
                if expanded != query_lower:
                    queries.append(expanded)
    
    return list(set(queries))[:3]

def hybrid_search(query: str, embedding: list, limit: int = 20):
    url = f"{SUPABASE_URL}/rest/v1/rpc/hybrid_search"
    r = requests.post(url, headers=HEADERS, json={
        "query_text": query,
        "query_embedding": embedding,
        "match_count": limit,
        "bm25_weight": 0.5,
        "vector_weight": 0.5
    })
    return r.json() if r.status_code == 200 else []

def advanced_search_v3(query: str, top_k: int = 5) -> list:
    """
    Pipeline v3:
    1. Extraer referencias exactas y buscarlas primero
    2. Query expansion
    3. Hybrid search
    4. Merge y rerank
    """
    all_results = {}
    
    # 1. Búsqueda exacta de referencias
    exact_refs = extract_exact_refs(query)
    for ref in exact_refs:
        exact_results = search_exact(ref)
        for r in exact_results:
            rid = r.get('id', '')
            r['hybrid_score'] = 1.0  # Score alto para matches exactos
            r['match_type'] = 'exact'
            all_results[rid] = r
    
    # 2. Query expansion + hybrid search
    queries = expand_query(query)
    
    for q in queries:
        response = client.embeddings.create(model="text-embedding-3-small", input=q)
        embedding = response.data[0].embedding
        
        results = hybrid_search(q, embedding, limit=15)
        
        for r in results:
            rid = r.get('id', '')
            if rid not in all_results:
                r['match_type'] = 'hybrid'
                all_results[rid] = r
            elif all_results[rid].get('match_type') != 'exact':
                existing = all_results[rid].get('hybrid_score', 0) or 0
                new = r.get('hybrid_score', 0) or 0
                all_results[rid]['hybrid_score'] = max(existing, new)
    
    # 3. Sort by score
    results = list(all_results.values())
    results.sort(key=lambda x: x.get('hybrid_score', 0) or 0, reverse=True)
    
    return results[:top_k]

# Evaluación
if __name__ == "__main__":
    test_cases = [
        {"query": "Tabla A.2.4-3", "expected": ["A.2.4-3", "Tabla A.2.4-3"]},
        {"query": "deriva máxima permitida 1.0%", "expected": ["A.6.4"]},
        {"query": "coeficiente Fa suelo tipo D", "expected": ["A.2.4"]},
        {"query": "¿Cómo calcular el cortante basal?", "expected": ["A.4.3", "cortante"]},
        {"query": "R0 para pórtico especial", "expected": ["A.3"]},
        {"query": "período fundamental Ta", "expected": ["A.4.2", "período"]},
        {"query": "zona sísmica Bogotá Aa Av", "expected": ["A-4", "A.2.3", "municipio"]},
        {"query": "espectro elástico aceleraciones", "expected": ["A.2.6"]},
        {"query": "requisitos estructura irregular", "expected": ["A.3.3", "irregular"]},
        {"query": "A.6.4.1 límite drift", "expected": ["A.6.4.1", "A.6.4"]},
    ]
    
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║         EVALUACIÓN v3: BÚSQUEDA EXACTA + HÍBRIDA                             ║")
    print("╠══════════════════════════════════════════════════════════════════════════════╣")
    print()
    
    passed = 0
    for tc in test_cases:
        results = advanced_search_v3(tc["query"], 5)
        
        found = False
        found_in = None
        for i, r in enumerate(results[:3]):
            section = (r.get('section_path', '') or '').lower()
            title = (r.get('title', '') or '').lower()
            content = (r.get('content', '') or '')[:200].lower()
            
            for exp in tc["expected"]:
                if exp.lower() in section or exp.lower() in title or exp.lower() in content:
                    found = True
                    found_in = i + 1
                    break
            if found:
                break
        
        if found:
            passed += 1
            match_type = results[found_in-1].get('match_type', '?') if results else '?'
            print(f"  ✓ [{found_in}/{match_type[:3]}] {tc['query'][:42]:42}")
        else:
            top = results[0].get('section_path', '') if results else 'N/A'
            print(f"  ✗ [X]     {tc['query'][:42]:42} → {top[:25]}")
    
    print()
    print(f"╠══════════════════════════════════════════════════════════════════════════════╣")
    print(f"║  RESULTADO: {passed}/{len(test_cases)} ({passed/len(test_cases)*100:.0f}%)                                                    ║")
    print(f"╚══════════════════════════════════════════════════════════════════════════════╝")
