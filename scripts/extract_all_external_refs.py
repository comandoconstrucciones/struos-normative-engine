#!/usr/bin/env python3
"""
Extrae TODAS las referencias externas del texto completo del Título A
Detecta normas inline, en secciones dedicadas, y al final de capítulos
"""
import json
import re
from collections import defaultdict

# Patrones para detectar normas externas
NORM_PATTERNS = [
    # ASTM con número y año opcional
    (r'ASTM\s+[A-Z]?\d+(?:-\d+)?(?:\s*\(\d{4}\))?', 'ASTM'),
    # ASCE/SEI con número
    (r'ASCE(?:/SEI)?\s+\d+(?:-\d+)?', 'ASCE'),
    # ACI con número
    (r'ACI\s+\d+(?:-\d+)?', 'ACI'),
    # FEMA con número
    (r'FEMA\s+\d+[a-zA-Z]?', 'FEMA'),
    # NTC con número
    (r'NTC\s+\d+(?:-\d+)?(?:\s*\(\d{4}\))?', 'NTC'),
    # AWS con código
    (r'AWS\s+[A-Z]\d+\.\d+(?:-\d+)?', 'AWS'),
    # ISO con número
    (r'ISO\s+\d+(?:-\d+)?', 'ISO'),
    # AISC con número
    (r'AISC\s+\d+(?:-\d+)?', 'AISC'),
    # Eurocode
    (r'EN\s+\d+(?:-\d+)?(?:-\d+)?', 'EUROCODE'),
    # IBC
    (r'IBC\s+\d{4}', 'IBC'),
]

def extract_norms_from_text(text):
    """Extrae todas las normas mencionadas en un texto"""
    found = []
    for pattern, norm_type in NORM_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            # Normalizar el código
            code = m.upper().strip()
            code = re.sub(r'\s+', ' ', code)
            found.append({
                'code': code,
                'type': norm_type
            })
    return found

def main():
    with open('extracted/titulo_a/complete_extraction.json', 'r') as f:
        data = json.load(f)
    
    # Diccionario: sección -> normas citadas
    section_refs = defaultdict(list)
    # Diccionario: norma -> secciones donde se cita
    norm_citations = defaultdict(list)
    # Todas las normas únicas
    all_norms = {}
    
    total_pages = len(data['pages'])
    print(f"Escaneando {total_pages} páginas...")
    
    for page in data['pages']:
        page_num = page['page_number']
        
        for elem in page.get('elements', []):
            section = elem.get('section_path', f'page_{page_num}')
            content = elem.get('content', '')
            
            if isinstance(content, list):
                content = ' '.join(str(c) for c in content)
            if not isinstance(content, str):
                continue
            
            # Extraer normas del contenido
            norms = extract_norms_from_text(content)
            
            for norm in norms:
                code = norm['code']
                norm_type = norm['type']
                
                # Agregar a las referencias de la sección
                if code not in [n['code'] for n in section_refs[section]]:
                    section_refs[section].append(norm)
                
                # Agregar a las citaciones de la norma
                if section not in norm_citations[code]:
                    norm_citations[code].append(section)
                
                # Agregar a normas únicas
                if code not in all_norms:
                    all_norms[code] = {
                        'code': code,
                        'type': norm_type,
                        'citations': []
                    }
    
    # Compilar resultados
    results = {
        'total_unique_norms': len(all_norms),
        'norms_by_type': defaultdict(list),
        'norms': [],
        'section_to_norms': {},
        'edges': []
    }
    
    # Agrupar por tipo
    for code, norm_data in all_norms.items():
        norm_type = norm_data['type']
        results['norms_by_type'][norm_type].append(code)
        
        citations = norm_citations[code]
        results['norms'].append({
            'code': code,
            'type': norm_type,
            'cited_in': citations,
            'citation_count': len(citations)
        })
        
        # Crear aristas
        for section in citations:
            results['edges'].append({
                'source_section': section,
                'target_norm': code,
                'relation': 'CITES'
            })
    
    # Secciones con sus normas
    for section, norms in section_refs.items():
        if norms:
            results['section_to_norms'][section] = [n['code'] for n in norms]
    
    # Guardar resultados
    with open('extracted/external_refs_complete.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=list)
    
    # Resumen
    print(f"\n=== RESUMEN ===")
    print(f"Normas únicas encontradas: {len(all_norms)}")
    print(f"\nPor tipo:")
    for norm_type, codes in sorted(results['norms_by_type'].items()):
        print(f"  {norm_type}: {len(codes)}")
    
    print(f"\nAristas de citación: {len(results['edges'])}")
    print(f"Secciones con referencias: {len(results['section_to_norms'])}")
    
    # Top normas más citadas
    print(f"\nTop 10 normas más citadas:")
    sorted_norms = sorted(results['norms'], key=lambda x: -x['citation_count'])
    for n in sorted_norms[:10]:
        print(f"  {n['code']}: {n['citation_count']} citaciones")
    
    print(f"\nArchivo generado: extracted/external_refs_complete.json")

if __name__ == '__main__':
    main()
