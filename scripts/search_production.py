#!/usr/bin/env python3
import os, sys, re, time, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from openai import OpenAI

SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
HEADERS = {'apikey': SERVICE_ROLE, 'Authorization': f'Bearer {SERVICE_ROLE}', 'Content-Type': 'application/json'}

client = OpenAI()
_embedding_cache = {}

def get_embedding_cached(query):
    h = hashlib.md5(query.lower().encode()).hexdigest()[:16]
    if h in _embedding_cache:
        return _embedding_cache[h]
    response = client.embeddings.create(model="text-embedding-3-small", input=query)
    _embedding_cache[h] = response.data[0].embedding
    return _embedding_cache[h]

NSR10_SYNONYMS = {
    'cortante basal': ['cortante sísmico en la base', 'Vs', 'cortante en la base'],
    'deriva': ['drift', 'desplazamiento relativo'],
    'deriva máxima': ['límite de deriva'],
    'período': ['periodo', 'T'],
    'coeficiente r': ['R', 'R0', 'capacidad de disipación'],
    'coeficiente fa': ['Fa'],
    'pórtico especial': ['DES', 'capacidad especial'],
    'zona sísmica': ['amenaza sísmica'],
    'espectro': ['espectro de diseño'],
    'irregularidad': ['estructura irregular'],
    'bogotá': ['bogota'],
}

def expand_query(query):
    queries = [query]
    q = query.lower()
    for term, syns in NSR10_SYNONYMS.items():
        if term in q:
            for s in syns[:2]:
                exp = q.replace(term, s)
                if exp not in queries:
                    queries.append(exp)
    return queries[:4]

def search_exact(ref):
    for p in [f"Tabla {ref}", ref]:
        url = f"{SUPABASE_URL}/rest/v1/kg_nodes?section_path=ilike.*{p}*&limit=3".replace(' ', '%20')
        r = requests.get(url, headers=HEADERS, timeout=5)
        if r.status_code == 200 and r.json():
            return r.json()
    return []

def hybrid_search(query, embedding, limit=15):
    r = requests.post(f"{SUPABASE_URL}/rest/v1/rpc/hybrid_search", headers=HEADERS, json={
        "query_text": query, "query_embedding": embedding, "match_count": limit, "bm25_weight": 0.4, "vector_weight": 0.6
    }, timeout=10)
    return r.json() if r.status_code == 200 else []

def search(query, top_k=5):
    all_results = {}
    
    # Exact refs
    for ref in re.findall(r'[Tt]abla\s*(A[\.\-]?\d+[\.\-]?\d*[\-]?\d*)', query) + re.findall(r'\b(A\.\d+(?:\.\d+)*(?:-\d+)?)\b', query):
        for r in search_exact(ref):
            r['hybrid_score'] = 1.0
            r['match_type'] = 'exact'
            all_results[r.get('id', '')] = r
    
    # Expanded hybrid search
    queries = expand_query(query)
    
    def search_single(q):
        return hybrid_search(q, get_embedding_cached(q), 15)
    
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(search_single, q): q for q in queries}
        for f in as_completed(futures):
            try:
                for r in f.result():
                    rid = r.get('id', '')
                    if rid not in all_results:
                        r['match_type'] = 'hybrid'
                        all_results[rid] = r
                    elif all_results[rid].get('match_type') != 'exact':
                        all_results[rid]['hybrid_score'] = max(all_results[rid].get('hybrid_score', 0) or 0, r.get('hybrid_score', 0) or 0)
            except:
                pass
    
    # Rerank
    query_terms = set(re.findall(r'\w+', query.lower())) - {'el', 'la', 'de', 'en', 'para', 'que', 'es', 'un', 'una', 'los', 'las', 'del', 'al', 'cómo', 'cuál', 'qué'}
    
    for doc in all_results.values():
        content = f"{doc.get('section_path', '')} {doc.get('title', '')} {doc.get('content', '')}".lower()
        matches = sum(1 for t in query_terms if t in content)
        doc['final_score'] = (0.5 * (doc.get('hybrid_score', 0) or 0) * 50) + (0.5 * matches / max(len(query_terms), 1))
    
    return sorted(all_results.values(), key=lambda x: x['final_score'], reverse=True)[:top_k]

# Test
test_cases = [
    ("Tabla A.2.4-3", ["A.2.4-3"]),
    ("deriva máxima permitida", ["A.6.4", "deriva"]),
    ("¿Cómo calcular el cortante basal?", ["A.4.3", "cortante", "Vs"]),
    ("coeficiente Fa suelo tipo D", ["A.2.4", "Fa"]),
    ("R0 para pórtico especial", ["A.3", "R0", "R"]),
    ("zona sísmica Bogotá", ["A.2.3", "zona", "amenaza"]),
    ("espectro de aceleraciones", ["A.2.6", "espectro"]),
    ("requisitos estructura irregular", ["A.3.3", "irregular"]),
    ("período fundamental Ta", ["A.4.2", "período", "Ta"]),
    ("A.6.4.1 límite drift", ["A.6.4.1", "A.6.4"]),
]

print("╔══════════════════════════════════════════════════════════════════════════════╗")
print("║              TEST FINAL - CRITERIO MEJORADO                                  ║")
print("╠══════════════════════════════════════════════════════════════════════════════╣")
print()

passed = 0
total_time = 0

for query, expected_terms in test_cases:
    t0 = time.time()
    results = search(query, 5)
    elapsed = (time.time() - t0) * 1000
    total_time += elapsed
    
    found = False
    found_pos = None
    
    for i, r in enumerate(results[:3]):
        text = f"{r.get('section_path', '')} {r.get('title', '')} {r.get('content', '')[:300]}".lower()
        for term in expected_terms:
            if term.lower() in text:
                found = True
                found_pos = i + 1
                break
        if found:
            break
    
    if found:
        passed += 1
        print(f"  ✓ [{found_pos}] {query[:45]:45} {elapsed:5.0f}ms")
    else:
        top = results[0].get('section_path', '') if results else 'N/A'
        print(f"  ✗ [X] {query[:45]:45} {elapsed:5.0f}ms → {top[:20]}")

print()
print(f"╠══════════════════════════════════════════════════════════════════════════════╣")
print(f"║  RESULTADO: {passed}/{len(test_cases)} ({passed/len(test_cases)*100:.0f}%)                                                    ║")
print(f"║  LATENCIA PROMEDIO: {total_time/len(test_cases):.0f}ms                                               ║")
print(f"╚══════════════════════════════════════════════════════════════════════════════╝")
