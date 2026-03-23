#!/usr/bin/env python3
import os, json, requests, uuid, re, hashlib

SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
HEADERS = {
    'apikey': SERVICE_ROLE,
    'Authorization': f'Bearer {SERVICE_ROLE}',
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal'
}

def insert_nodes(nodes):
    url = f"{SUPABASE_URL}/rest/v1/kg_nodes"
    inserted = 0
    for i in range(0, len(nodes), 50):
        batch = nodes[i:i+50]
        r = requests.post(url, headers=HEADERS, json=batch)
        if r.status_code in [200, 201]:
            inserted += len(batch)
    return inserted

def main():
    with open('extracted/symbols_all_chapters.json', 'r') as f:
        symbols = json.load(f)
    
    nodes = []
    seen = set()
    
    for s in symbols:
        symbol = s.get('symbol', '')
        chapter = s.get('chapter', 'A')
        definition = s.get('definition', '') or ''
        
        # Crear hash único del contenido
        content_hash = hashlib.md5(f"{symbol}{definition}".encode()).hexdigest()[:8]
        key = f"{chapter}_{symbol}_{content_hash}"
        
        if key in seen or not symbol:
            continue
        seen.add(key)
        
        # section_path único usando hash
        section_path = f"SYM.{chapter.replace('.','_')}.{content_hash}"
        
        content = definition
        if s.get('unit'):
            content += f" [Unidad: {s['unit']}]"
        if s.get('reference'):
            content += f" ({s['reference']})"
        
        nodes.append({
            'id': str(uuid.uuid4()),
            'norm_code': 'NSR-10',
            'section_path': section_path,
            'type': 'SYMBOL',
            'title': symbol,
            'content': content,
            'content_summary': f"Símbolo {symbol} - {chapter}",
            'page_start': s.get('source_page')
        })
    
    print(f"Insertando {len(nodes)} símbolos...")
    inserted = insert_nodes(nodes)
    print(f"Insertados: {inserted}")

if __name__ == '__main__':
    main()
