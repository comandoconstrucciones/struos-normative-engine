#!/usr/bin/env python3
"""
Crea conexiones avanzadas en el Knowledge Graph:
1. APPLIES_TO: Tabla → Fórmulas que usan datos de esa tabla
2. DEFINED_IN: Símbolo → Sección donde se define
3. Referencias cruzadas internas adicionales
"""
import os, json, re, requests, uuid

SUPABASE_URL = os.environ.get('STRUOS_SUPABASE_URL')
SERVICE_ROLE = os.environ.get('STRUOS_SUPABASE_SERVICE_ROLE')
HEADERS = {'apikey': SERVICE_ROLE, 'Authorization': f'Bearer {SERVICE_ROLE}', 'Content-Type': 'application/json', 'Range': '0-2000'}

def get_all(endpoint, params=""):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}?{params}"
    return requests.get(url, headers=HEADERS).json()

def insert_edges(edges):
    if not edges:
        return 0
    url = f"{SUPABASE_URL}/rest/v1/kg_edges"
    inserted = 0
    for i in range(0, len(edges), 50):
        batch = edges[i:i+50]
        r = requests.post(url, headers=HEADERS, json=batch)
        if r.status_code in [200, 201]:
            inserted += len(batch)
    return inserted

def main():
    print("=== CREANDO CONEXIONES AVANZADAS ===\n")
    
    # Obtener datos
    print("Obteniendo datos del KG...")
    tables = get_all("kg_nodes", "type=eq.TABLE&select=id,title,section_path,table_headers")
    formulas = get_all("kg_nodes", "type=eq.FORMULA&select=id,section_path,formula_latex,formula_variables")
    symbols = get_all("kg_nodes", "type=eq.SYMBOL&select=id,title,section_path,content_summary")
    sections = get_all("kg_nodes", "select=id,section_path,content,type")
    
    print(f"  Tablas: {len(tables)}")
    print(f"  Fórmulas: {len(formulas)}")
    print(f"  Símbolos: {len(symbols)}")
    print(f"  Secciones: {len(sections)}")
    
    all_edges = []
    
    # ═══════════════════════════════════════════════════════════════
    # 1. APPLIES_TO: Tabla → Fórmulas que usan datos de esa tabla
    # ═══════════════════════════════════════════════════════════════
    print("\n1. Creando APPLIES_TO (Tabla → Fórmula)...")
    
    # Mapeo de tablas importantes a los símbolos que proveen
    table_symbols = {
        'A.2.4-3': ['Fa', 'fa'],           # Coeficiente Fa
        'A.2.4-4': ['Fv', 'fv'],           # Coeficiente Fv
        'A.2.5-1': ['I'],                   # Coeficiente importancia
        'A.2.3-1': ['Aa', 'Av'],           # Amenaza sísmica
        'A.4.2-1': ['Ct', 'C_t', 'α'],     # Período aproximado
        'A.6.4-1': ['deriva', 'Δ'],        # Derivas
        'A.3-6': ['φp', 'phi_p'],          # Irregularidades planta
        'A.3-7': ['φa', 'phi_a'],          # Irregularidades altura
    }
    
    # Crear mapa tabla_id
    table_map = {}
    for t in tables:
        title = t.get('title', '') or ''
        section = t.get('section_path', '') or ''
        for table_id in table_symbols.keys():
            if table_id in title or table_id in section:
                table_map[table_id] = t['id']
    
    applies_edges = []
    for f in formulas:
        latex = f.get('formula_latex', '') or ''
        variables = f.get('formula_variables', {}) or {}
        
        # Buscar qué símbolos usa
        for table_id, syms in table_symbols.items():
            if table_id not in table_map:
                continue
            
            for sym in syms:
                # Buscar en LaTeX o variables
                if sym.lower() in latex.lower() or (isinstance(variables, dict) and sym in variables):
                    applies_edges.append({
                        'id': str(uuid.uuid4()),
                        'source_id': table_map[table_id],
                        'target_id': f['id'],
                        'edge_type': 'APPLIES_TO'
                    })
                    break
    
    # Eliminar duplicados
    seen = set()
    applies_edges = [e for e in applies_edges if (e['source_id'], e['target_id']) not in seen and not seen.add((e['source_id'], e['target_id']))]
    
    print(f"  Aristas APPLIES_TO: {len(applies_edges)}")
    all_edges.extend(applies_edges)
    
    # ═══════════════════════════════════════════════════════════════
    # 2. DEFINED_IN: Símbolo → Sección donde se define
    # ═══════════════════════════════════════════════════════════════
    print("\n2. Creando DEFINED_IN (Símbolo → Sección)...")
    
    # Crear mapa de secciones
    section_map = {s['section_path']: s['id'] for s in sections if s.get('section_path')}
    
    defined_edges = []
    for sym in symbols:
        sym_section = sym.get('section_path', '') or ''
        summary = sym.get('content_summary', '') or ''
        
        # Extraer capítulo del símbolo (ej: "A.2" de "SYM.A_2.xxx")
        match = re.search(r'A[._](\d+)', sym_section)
        if match:
            chapter = f"A.{match.group(1)}"
            nomenclatura = f"{chapter}.0"
            
            # Buscar la sección de nomenclatura
            for sec_path, sec_id in section_map.items():
                if nomenclatura in sec_path:
                    defined_edges.append({
                        'id': str(uuid.uuid4()),
                        'source_id': sym['id'],
                        'target_id': sec_id,
                        'edge_type': 'DEFINED_IN'
                    })
                    break
    
    print(f"  Aristas DEFINED_IN: {len(defined_edges)}")
    all_edges.extend(defined_edges)
    
    # ═══════════════════════════════════════════════════════════════
    # 3. REFERENCES: Referencias cruzadas internas adicionales
    # ═══════════════════════════════════════════════════════════════
    print("\n3. Buscando referencias cruzadas adicionales...")
    
    ref_patterns = [
        r'[Vv][ée]ase\s+(?:la\s+)?(?:secci[oó]n\s+)?(A\.\d+(?:\.\d+)*(?:\.\d+)*)',
        r'[Vv]er\s+(?:la\s+)?(?:secci[oó]n\s+)?(A\.\d+(?:\.\d+)*)',
        r'[Ss]eg[uú]n\s+(?:lo\s+)?(?:establecido\s+en\s+)?(A\.\d+(?:\.\d+)*)',
        r'[Dd]e\s+acuerdo\s+con\s+(A\.\d+(?:\.\d+)*)',
        r'[Cc]onforme\s+a\s+(A\.\d+(?:\.\d+)*)',
        r'[Dd]efinid[oa]\s+en\s+(A\.\d+(?:\.\d+)*)',
        r'[Ee]cuaci[oó]n\s+(A\.\d+(?:[.-]\d+)*)',
        r'[Tt]abla\s+(A\.\d+(?:[.-]\d+)*)',
        r'[Ff]igura\s+(A\.\d+(?:[.-]\d+)*)',
        r'[Cc]ap[ií]tulo\s+(A\.\d+)',
    ]
    
    ref_edges = []
    existing_refs = set()  # Para evitar duplicados
    
    for s in sections:
        content = s.get('content', '') or ''
        source_id = s['id']
        source_path = s.get('section_path', '')
        
        for pattern in ref_patterns:
            matches = re.findall(pattern, content)
            for ref in matches:
                ref = ref.strip()
                
                # Buscar la sección referenciada
                target_id = None
                for sec_path, sec_id in section_map.items():
                    if ref == sec_path or sec_path.startswith(ref + '.') or sec_path.endswith(ref):
                        target_id = sec_id
                        break
                
                if target_id and target_id != source_id:
                    edge_key = (source_id, target_id)
                    if edge_key not in existing_refs:
                        existing_refs.add(edge_key)
                        ref_edges.append({
                            'id': str(uuid.uuid4()),
                            'source_id': source_id,
                            'target_id': target_id,
                            'edge_type': 'REFERENCES'
                        })
    
    print(f"  Aristas REFERENCES adicionales: {len(ref_edges)}")
    all_edges.extend(ref_edges)
    
    # ═══════════════════════════════════════════════════════════════
    # 4. REQUIRES: Dependencias entre fórmulas
    # ═══════════════════════════════════════════════════════════════
    print("\n4. Buscando dependencias entre fórmulas...")
    
    formula_map = {f['section_path']: f['id'] for f in formulas if f.get('section_path')}
    
    requires_edges = []
    for f in formulas:
        latex = f.get('formula_latex', '') or ''
        content = f.get('formula_variables', {})
        if isinstance(content, dict):
            content = str(content)
        
        # Buscar referencias a otras ecuaciones
        eq_refs = re.findall(r'[Ee]cuaci[oó]n\s+(A\.\d+(?:[.-]\d+)*)', content + latex)
        for eq_ref in eq_refs:
            # Buscar la fórmula referenciada
            for f_path, f_id in formula_map.items():
                if eq_ref in f_path and f_id != f['id']:
                    requires_edges.append({
                        'id': str(uuid.uuid4()),
                        'source_id': f['id'],
                        'target_id': f_id,
                        'edge_type': 'REQUIRES'
                    })
                    break
    
    print(f"  Aristas REQUIRES: {len(requires_edges)}")
    all_edges.extend(requires_edges)
    
    # ═══════════════════════════════════════════════════════════════
    # Insertar todas las aristas
    # ═══════════════════════════════════════════════════════════════
    print(f"\n=== INSERTANDO {len(all_edges)} ARISTAS ===")
    inserted = insert_edges(all_edges)
    print(f"  Insertadas: {inserted}")
    
    # Resumen final
    print("\n=== RESUMEN ===")
    print(f"  APPLIES_TO (Tabla→Fórmula): {len(applies_edges)}")
    print(f"  DEFINED_IN (Símbolo→Sección): {len(defined_edges)}")
    print(f"  REFERENCES (referencias cruzadas): {len(ref_edges)}")
    print(f"  REQUIRES (dependencia fórmulas): {len(requires_edges)}")
    print(f"  TOTAL insertadas: {inserted}")

if __name__ == '__main__':
    main()
