#!/usr/bin/env python3
"""
Cache de embeddings para evitar recalcular
Usa Supabase como storage (sin Redis)
"""
import os, hashlib, json, requests
from openai import OpenAI

SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
HEADERS = {'apikey': SERVICE_ROLE, 'Authorization': f'Bearer {SERVICE_ROLE}', 'Content-Type': 'application/json'}

client = OpenAI()

# Cache en memoria (para la sesión)
_memory_cache = {}

def get_query_hash(query: str) -> str:
    """Genera hash único para el query"""
    return hashlib.md5(query.lower().strip().encode()).hexdigest()[:16]

def get_cached_embedding(query: str) -> list | None:
    """Busca embedding en cache"""
    query_hash = get_query_hash(query)
    
    # 1. Buscar en memoria
    if query_hash in _memory_cache:
        return _memory_cache[query_hash]
    
    # 2. Buscar en Supabase (tabla embedding_cache)
    try:
        url = f"{SUPABASE_URL}/rest/v1/embedding_cache?query_hash=eq.{query_hash}&select=embedding"
        r = requests.get(url, headers=HEADERS, timeout=2)
        if r.status_code == 200:
            data = r.json()
            if data:
                embedding = data[0].get('embedding')
                _memory_cache[query_hash] = embedding  # Guardar en memoria
                return embedding
    except:
        pass
    
    return None

def save_embedding_to_cache(query: str, embedding: list):
    """Guarda embedding en cache"""
    query_hash = get_query_hash(query)
    
    # 1. Guardar en memoria
    _memory_cache[query_hash] = embedding
    
    # 2. Guardar en Supabase (async, no bloquea)
    try:
        url = f"{SUPABASE_URL}/rest/v1/embedding_cache"
        payload = {
            'query_hash': query_hash,
            'query_text': query[:200],  # Guardar primeros 200 chars
            'embedding': embedding
        }
        # Upsert
        requests.post(url, headers={**HEADERS, 'Prefer': 'resolution=merge-duplicates'}, 
                     json=payload, timeout=2)
    except:
        pass  # No fallar si cache falla

def get_embedding(query: str, use_cache: bool = True) -> list:
    """
    Obtiene embedding, usando cache si disponible
    """
    if use_cache:
        cached = get_cached_embedding(query)
        if cached:
            return cached
    
    # Generar nuevo embedding
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )
    embedding = response.data[0].embedding
    
    # Guardar en cache
    if use_cache:
        save_embedding_to_cache(query, embedding)
    
    return embedding

# Stats
def get_cache_stats():
    """Estadísticas del cache"""
    return {
        'memory_entries': len(_memory_cache),
    }

if __name__ == "__main__":
    import time
    
    print("=== TEST DE CACHE ===")
    
    query = "deriva máxima permitida"
    
    # Primera vez (sin cache)
    t0 = time.time()
    emb1 = get_embedding(query, use_cache=True)
    t1 = time.time() - t0
    print(f"Primera vez: {t1*1000:.0f}ms (genera embedding)")
    
    # Segunda vez (con cache)
    t0 = time.time()
    emb2 = get_embedding(query, use_cache=True)
    t2 = time.time() - t0
    print(f"Segunda vez: {t2*1000:.0f}ms (desde cache)")
    
    print(f"Speedup: {t1/t2:.0f}x")
    print(f"Cache stats: {get_cache_stats()}")
