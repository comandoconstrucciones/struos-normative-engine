#!/usr/bin/env python3
"""
Carga normas externas y aristas de citación al Knowledge Graph
"""
import os
import json
import requests
import uuid

SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
HEADERS = {
    'apikey': SERVICE_ROLE,
    'Authorization': f'Bearer {SERVICE_ROLE}',
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal'
}

def get_existing_sections():
    """Obtiene IDs de secciones existentes en el KG"""
    url = f"{SUPABASE_URL}/rest/v1/kg_nodes?select=id,section_path"
    r = requests.get(url, headers=HEADERS)
    data = r.json()
    return {d['section_path']: d['id'] for d in data if d.get('section_path')}

def insert_nodes(nodes):
    url = f"{SUPABASE_URL}/rest/v1/kg_nodes"
    inserted = 0
    for i in range(0, len(nodes), 50):
        batch = nodes[i:i+50]
        r = requests.post(url, headers=HEADERS, json=batch)
        if r.status_code in [200, 201]:
            inserted += len(batch)
    return inserted

def insert_edges(edges):
    url = f"{SUPABASE_URL}/rest/v1/kg_edges"
    inserted = 0
    for i in range(0, len(edges), 50):
        batch = edges[i:i+50]
        r = requests.post(url, headers=HEADERS, json=batch)
        if r.status_code in [200, 201]:
            inserted += len(batch)
    return inserted

def main():
    with open('extracted/external_refs_complete.json', 'r') as f:
        data = json.load(f)
    
    # Obtener secciones existentes
    print("Obteniendo secciones existentes...")
    existing = get_existing_sections()
    print(f"  {len(existing)} secciones en KG")
    
    # Crear nodos para normas externas
    nodes = []
    norm_ids = {}  # code -> uuid
    
    print(f"\nCreando nodos para {len(data['norms'])} normas externas...")
    for norm in data['norms']:
        code = norm['code']
        norm_type = norm['type']
        
        node_id = str(uuid.uuid4())
        norm_ids[code] = node_id
        
        code_slug = code.replace(' ', '_').replace('/', '_').replace('-', '_')
        
        nodes.append({
            'id': node_id,
            'norm_code': 'EXTERNAL',
            'section_path': f"REF.{code_slug}",
            'type': 'EXTERNAL_REF',
            'title': code,
            'content': f"Norma externa {norm_type}: {code}",
            'content_summary': f"{norm_type} - citada {norm['citation_count']} veces en NSR-10 Título A"
        })
    
    inserted_nodes = insert_nodes(nodes)
    print(f"  Nodos insertados: {inserted_nodes}")
    
    # Crear aristas de citación
    edges = []
    print(f"\nCreando aristas de citación...")
    
    for edge_data in data['edges']:
        source_section = edge_data['source_section']
        target_norm = edge_data['target_norm']
        
        # Buscar ID de la sección fuente
        source_id = existing.get(source_section)
        target_id = norm_ids.get(target_norm)
        
        if source_id and target_id:
            edges.append({
                'id': str(uuid.uuid4()),
                'source_id': source_id,
                'target_id': target_id,
                'edge_type': 'CITES'
            })
    
    print(f"  Aristas válidas: {len(edges)} de {len(data['edges'])}")
    
    if edges:
        inserted_edges = insert_edges(edges)
        print(f"  Aristas insertadas: {inserted_edges}")
    
    print(f"\n=== RESUMEN ===")
    print(f"Normas externas: {len(nodes)}")
    print(f"Aristas CITES: {len(edges)}")

if __name__ == '__main__':
    main()
