"""
link_glossary.py — Conecta definiciones extraídas del PDF al glosario normalizado.

Crea aristas DEFINES entre términos del glosario y las secciones donde se usan.
"""

import json
import re
from typing import Dict, List, Set, Tuple
from pathlib import Path

# Rutas
BASE_DIR = Path(__file__).parent.parent
EXTRACTION_FILE = BASE_DIR / "extracted/titulo_a/complete_extraction.json"
GLOSSARY_FILE = BASE_DIR / "data/nsr10_glossary.json"
OUTPUT_FILE = BASE_DIR / "data/glossary_links.json"


def load_data() -> Tuple[dict, dict]:
    """Carga extracción y glosario."""
    with open(EXTRACTION_FILE) as f:
        extraction = json.load(f)
    with open(GLOSSARY_FILE) as f:
        glossary = json.load(f)
    return extraction, glossary


def find_term_in_text(text: str, term: str) -> List[int]:
    """Encuentra todas las posiciones de un término en el texto."""
    # Buscar término exacto o con variantes
    patterns = [
        rf'\b{re.escape(term)}\b',  # término exacto
        rf'\b{re.escape(term.lower())}\b',  # minúsculas
    ]
    
    positions = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            positions.append(match.start())
    
    return positions


def link_glossary_to_sections(extraction: dict, glossary: dict) -> Dict:
    """
    Para cada término del glosario, encuentra las secciones donde aparece.
    """
    terms = glossary["terms"]
    links = {}
    
    print(f"Buscando {len(terms)} términos en {len(extraction['pages'])} páginas...")
    
    for term_id, term_data in terms.items():
        term = term_data["term"]
        links[term_id] = {
            "term": term,
            "definition": term_data["definition"],
            "defined_in": term_data.get("section", ""),
            "references": [],  # Secciones donde aparece
            "count": 0
        }
        
        # Buscar en todas las páginas
        for page in extraction["pages"]:
            for element in page.get("elements", []):
                content = element.get("content", "") or ""
                section_path = element.get("section_path", "")
                
                # Saltar si no hay contenido
                if not content or len(content) < 5:
                    continue
                
                # Buscar término
                positions = find_term_in_text(content, term)
                
                if positions:
                    links[term_id]["count"] += len(positions)
                    
                    if section_path and section_path not in links[term_id]["references"]:
                        links[term_id]["references"].append(section_path)
    
    return links


def extract_implicit_definitions(extraction: dict) -> List[Dict]:
    """
    Extrae definiciones implícitas de las secciones tipo DEFINITION.
    """
    definitions = []
    
    for page in extraction["pages"]:
        for element in page.get("elements", []):
            if element.get("type") == "DEFINITION":
                content = element.get("content", "")
                section = element.get("section_path", "")
                
                # Extraer término (antes del '=' o ':')
                term = None
                definition = content
                
                # Patrones comunes
                if "=" in content:
                    parts = content.split("=", 1)
                    term = parts[0].strip()
                    definition = parts[1].strip() if len(parts) > 1 else ""
                elif ":" in content[:50]:
                    parts = content.split(":", 1)
                    term = parts[0].strip()
                    definition = parts[1].strip() if len(parts) > 1 else ""
                elif content.startswith("T"):
                    # Como "To = periodo de vibración..."
                    match = re.match(r'^([A-Za-z_0-9]+)\s*[=:–]\s*(.+)', content)
                    if match:
                        term = match.group(1).strip()
                        definition = match.group(2).strip()
                
                if term:
                    definitions.append({
                        "term": term,
                        "definition": definition[:200],
                        "section": section,
                        "page": page["page_number"]
                    })
    
    return definitions


def generate_report(links: Dict, implicit_defs: List[Dict]) -> str:
    """Genera reporte de conexiones."""
    report = []
    report.append("=" * 60)
    report.append("REPORTE DE CONEXIONES GLOSARIO ↔ SECCIONES")
    report.append("=" * 60)
    
    # Términos más referenciados
    sorted_terms = sorted(links.items(), key=lambda x: x[1]["count"], reverse=True)
    
    report.append("\n### TÉRMINOS MÁS REFERENCIADOS")
    for term_id, data in sorted_terms[:15]:
        refs = len(data["references"])
        count = data["count"]
        report.append(f"  {data['term']:12} → {count:4} menciones en {refs:3} secciones")
    
    # Términos sin referencias (posible error)
    no_refs = [t for t, d in links.items() if d["count"] == 0]
    if no_refs:
        report.append(f"\n### TÉRMINOS SIN REFERENCIAS ({len(no_refs)})")
        for t in no_refs[:10]:
            report.append(f"  ⚠ {t}")
    
    # Definiciones implícitas
    report.append(f"\n### DEFINICIONES EXTRAÍDAS DEL PDF ({len(implicit_defs)})")
    for d in implicit_defs[:10]:
        report.append(f"  [{d['section'] or 'N/A'}] {d['term']}: {d['definition'][:60]}...")
    
    report.append("\n" + "=" * 60)
    
    return "\n".join(report)


def main():
    print("Cargando datos...")
    extraction, glossary = load_data()
    
    print("Conectando glosario con secciones...")
    links = link_glossary_to_sections(extraction, glossary)
    
    print("Extrayendo definiciones implícitas...")
    implicit_defs = extract_implicit_definitions(extraction)
    
    # Guardar resultados
    output = {
        "glossary_links": links,
        "implicit_definitions": implicit_defs,
        "stats": {
            "terms_in_glossary": len(links),
            "definitions_extracted": len(implicit_defs),
            "total_references": sum(d["count"] for d in links.values())
        }
    }
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nResultados guardados en: {OUTPUT_FILE}")
    
    # Mostrar reporte
    report = generate_report(links, implicit_defs)
    print(report)
    
    return output


if __name__ == "__main__":
    main()
