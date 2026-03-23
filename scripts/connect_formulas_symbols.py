#!/usr/bin/env python3
"""
Crea aristas USES_SYMBOL entre fórmulas y los símbolos que usan
"""
import os, json, re, requests, uuid

SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
HEADERS = {'apikey': SERVICE_ROLE, 'Authorization': f'Bearer {SERVICE_ROLE}', 'Content-Type': 'application/json'}

def main():
    # Obtener todas las fórmulas
    print("Obteniendo fórmulas...")
    url = f"{SUPABASE_URL}/rest/v1/kg_nodes?type=eq.FORMULA&select=id,section_path,formula_latex,formula_variables"
    formulas = requests.get(url, headers=HEADERS).json()
    print(f"  Total: {len(formulas)}")
    
    # Obtener todos los símbolos
    print("Obteniendo símbolos...")
    url = f"{SUPABASE_URL}/rest/v1/kg_nodes?type=eq.SYMBOL&select=id,title"
    symbols = requests.get(url, headers=HEADERS).json()
    print(f"  Total: {len(symbols)}")
    
    # Crear diccionario símbolo → id
    symbol_map = {}
    for s in symbols:
        title = s.get('title', '')
        if title:
            # Normalizar: quitar subíndices unicode
            normalized = re.sub(r'[₀₁₂₃₄₅₆₇₈₉ᵢⱼₖₙₘ]', '', title)
            symbol_map[title.lower()] = s['id']
            symbol_map[normalized.lower()] = s['id']
    
    print(f"  Símbolos mapeados: {len(symbol_map)}")
    
    # Buscar símbolos en cada fórmula
    edges = []
    for f in formulas:
        latex = f.get('formula_latex', '') or ''
        variables = f.get('formula_variables', {}) or {}
        
        # Extraer símbolos del LaTeX
        # Patrones: letras griegas, variables con subíndices, etc.
        found_symbols = set()
        
        # Desde formula_variables
        if isinstance(variables, dict):
            for var in variables.keys():
                found_symbols.add(var.lower())
        
        # Desde LaTeX (buscar \frac{X}{Y}, X_, etc.)
        latex_vars = re.findall(r'([A-Za-z][a-z]?(?:_[a-z0-9]+)?)', latex)
        for v in latex_vars:
            if len(v) <= 5:  # Evitar palabras largas
                found_symbols.add(v.lower())
        
        # Crear aristas
        for sym in found_symbols:
            if sym in symbol_map:
                edges.append({
                    'id': str(uuid.uuid4()),
                    'source_id': f['id'],
                    'target_id': symbol_map[sym],
                    'edge_type': 'USES_SYMBOL'
                })
    
    print(f"\nAristas USES_SYMBOL a crear: {len(edges)}")
    
    # Insertar aristas
    if edges:
        url = f"{SUPABASE_URL}/rest/v1/kg_edges"
        inserted = 0
        for i in range(0, len(edges), 50):
            batch = edges[i:i+50]
            r = requests.post(url, headers=HEADERS, json=batch)
            if r.status_code in [200, 201]:
                inserted += len(batch)
        print(f"  Insertadas: {inserted}")
    
    # También extraer referencias cruzadas (Véase A.X.X)
    print("\nBuscando referencias cruzadas...")
    url = f"{SUPABASE_URL}/rest/v1/kg_nodes?select=id,section_path,content&limit=500"
    sections = requests.get(url, headers=HEADERS).json()
    
    # Crear mapa section_path → id
    section_map = {s['section_path']: s['id'] for s in sections if s.get('section_path')}
    
    ref_edges = []
    for s in sections:
        content = s.get('content', '') or ''
        section_id = s['id']
        
        # Buscar "Véase A.X.X" o "ver A.X.X"
        refs = re.findall(r'[Vv][ée]ase\s+(A\.\d+(?:\.\d+)*)', content)
        refs += re.findall(r'[Vv]er\s+(A\.\d+(?:\.\d+)*)', content)
        
        for ref in refs:
            if ref in section_map and section_map[ref] != section_id:
                ref_edges.append({
                    'id': str(uuid.uuid4()),
                    'source_id': section_id,
                    'target_id': section_map[ref],
                    'edge_type': 'REFERENCES'
                })
    
    print(f"Aristas REFERENCES a crear: {len(ref_edges)}")
    
    if ref_edges:
        url = f"{SUPABASE_URL}/rest/v1/kg_edges"
        inserted = 0
        for i in range(0, len(ref_edges), 50):
            batch = ref_edges[i:i+50]
            r = requests.post(url, headers=HEADERS, json=batch)
            if r.status_code in [200, 201]:
                inserted += len(batch)
        print(f"  Insertadas: {inserted}")

if __name__ == '__main__':
    main()
