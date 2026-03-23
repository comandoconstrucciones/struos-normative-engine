#!/usr/bin/env python3
"""
Carga definiciones y normas técnicas al Knowledge Graph en Supabase
"""
import os
import json
import requests
import uuid
import re

SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL', 'https://vdakfewjadwaczulcmvj.supabase.co')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')

HEADERS = {
    'apikey': SERVICE_ROLE,
    'Authorization': f'Bearer {SERVICE_ROLE}',
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal'
}

def slugify(text):
    """Convierte texto a slug válido para section_path"""
    text = text.lower()
    text = re.sub(r'[^a-z0-9áéíóúñü]', '_', text)
    text = re.sub(r'_+', '_', text)
    return text[:50].strip('_')

def insert_nodes(nodes):
    url = f"{SUPABASE_URL}/rest/v1/kg_nodes"
    batch_size = 50
    inserted = 0
    
    for i in range(0, len(nodes), batch_size):
        batch = nodes[i:i+batch_size]
        response = requests.post(url, headers=HEADERS, json=batch)
        if response.status_code in [200, 201]:
            inserted += len(batch)
        elif response.status_code != 409:  # Ignorar duplicados
            print(f"Error batch {i}: {response.text[:80]}")
    
    return inserted

def insert_edges(edges):
    url = f"{SUPABASE_URL}/rest/v1/kg_edges"
    batch_size = 50
    inserted = 0
    
    for i in range(0, len(edges), batch_size):
        batch = edges[i:i+batch_size]
        response = requests.post(url, headers=HEADERS, json=batch)
        if response.status_code in [200, 201]:
            inserted += len(batch)
    
    return inserted

def main():
    with open('extracted/definitions_a13.json', 'r') as f:
        definitions = json.load(f)
    
    with open('extracted/normas_tecnicas.json', 'r') as f:
        normas = json.load(f)
    
    nodes = []
    node_ids = {}
    
    # Crear nodos para definiciones con section_path único
    print(f"Procesando {len(definitions)} definiciones...")
    for i, d in enumerate(definitions):
        node_id = str(uuid.uuid4())
        term = d.get('term', f'term_{i}')
        term_slug = slugify(term)
        section_path = f"A.13.1.{term_slug}"
        
        node_ids[term.lower()] = node_id
        
        nodes.append({
            'id': node_id,
            'norm_code': 'NSR-10',
            'section_path': section_path,
            'type': 'DEFINITION',
            'title': term,
            'content': d.get('definition', ''),
            'content_summary': f"Definición: {term}",
            'page_start': d.get('source_page')
        })
    
    # Crear nodos para normas técnicas
    print(f"Procesando {len(normas)} normas técnicas...")
    seen_codes = set()
    
    for n in normas:
        code = n.get('code', '')
        if code in seen_codes or not code:
            continue
        seen_codes.add(code)
        
        node_id = str(uuid.uuid4())
        code_slug = code.replace(' ', '_').replace('.', '_')
        node_ids[code.lower()] = node_id
        
        nodes.append({
            'id': node_id,
            'norm_code': 'EXTERNAL',
            'section_path': f"EXT.{code_slug}",
            'type': 'EXTERNAL_REF',
            'title': code,
            'content': n.get('title', ''),
            'content_summary': f"Norma técnica: {code}",
            'page_start': n.get('source_page')
        })
    
    # Insertar nodos
    print(f"\nInsertando {len(nodes)} nodos...")
    inserted_nodes = insert_nodes(nodes)
    print(f"  → {inserted_nodes} nodos insertados")
    
    # Crear aristas de equivalencia
    edges = []
    for n in normas:
        code = n.get('code', '')
        equiv = n.get('equivalent', '')
        if code and equiv:
            source = node_ids.get(code.lower())
            target = node_ids.get(equiv.lower())
            if source and target:
                edges.append({
                    'id': str(uuid.uuid4()),
                    'source_id': source,
                    'target_id': target,
                    'edge_type': 'EQUIVALENT'
                })
    
    if edges:
        print(f"\nInsertando {len(edges)} aristas de equivalencia...")
        inserted_edges = insert_edges(edges)
        print(f"  → {inserted_edges} aristas insertadas")
    
    print("\n=== RESUMEN ===")
    print(f"Definiciones procesadas: {len(definitions)}")
    print(f"Normas técnicas: {len(seen_codes)}")
    print(f"Nodos insertados: {inserted_nodes}")

if __name__ == '__main__':
    main()
