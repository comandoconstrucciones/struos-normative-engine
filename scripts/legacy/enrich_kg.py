#!/usr/bin/env python3
"""
Enriquece el Knowledge Graph NSR-10 con:
1. Títulos faltantes
2. Subsecciones (a), (b), (c) como nodos hijos
3. Variables de fórmulas parseadas
4. Funciones Python para fórmulas
5. Contenido completo de secciones
6. URLs de figuras
"""

import os
import re
import json
from pathlib import Path
from uuid import uuid4

os.environ["SUPABASE_URL"] = "https://vdakfewjadwaczulcmvj.supabase.co"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "sb_secret_NpAozZyaiDMU6sbiy46Ewg_ISFm9VJz"

from supabase import create_client

EXTRACTED_DIR = Path("/root/clawd/leonardo/projects/normative-engine/extracted/titulo_a")

db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])


def parse_formula_variables(latex: str) -> dict:
    """
    Extrae variables de una fórmula LaTeX.
    Retorna dict con nombre: descripción
    """
    if not latex:
        return {}
    
    # Patrones comunes de variables
    # Buscar letras griegas y latinas con subíndices
    variables = {}
    
    # Variables comunes en NSR-10
    known_vars = {
        "Sa": "Aceleración espectral",
        "Sv": "Velocidad espectral",
        "Sd": "Desplazamiento espectral",
        "T": "Periodo fundamental",
        "T_0": "Periodo inicial del espectro",
        "T_C": "Periodo de transición",
        "T_L": "Periodo largo",
        "Aa": "Coeficiente de aceleración pico efectiva",
        "Av": "Coeficiente de velocidad pico efectiva",
        "Fa": "Coeficiente de amplificación para periodos cortos",
        "Fv": "Coeficiente de amplificación para periodos largos",
        "I": "Coeficiente de importancia",
        "R": "Coeficiente de disipación de energía",
        "R_0": "Coeficiente básico de disipación",
        "Ω_0": "Factor de sobrerresistencia",
        "C_d": "Factor de amplificación de deflexiones",
        "C_u": "Coeficiente de límite superior del periodo",
        "C_t": "Coeficiente para periodo aproximado",
        "h": "Altura total de la edificación",
        "h_n": "Altura hasta el nivel n",
        "h_{pi}": "Altura de piso i",
        "Δ": "Deriva de piso",
        "Δ_{max}": "Deriva máxima",
        "V_s": "Cortante basal de diseño",
        "W": "Peso sísmico total",
        "g": "Aceleración de la gravedad",
        "α": "Exponente para periodo aproximado",
        "k": "Exponente de distribución vertical",
    }
    
    # Buscar variables en la fórmula
    for var, desc in known_vars.items():
        # Escapar caracteres especiales de LaTeX
        pattern = var.replace("_", r"[_{}]*").replace("{", r"\{?").replace("}", r"\}?")
        if re.search(pattern, latex, re.IGNORECASE):
            variables[var] = desc
    
    return variables


def generate_python_function(latex: str, variables: dict, section: str) -> str:
    """
    Genera una función Python básica para la fórmula.
    """
    if not latex or not variables:
        return None
    
    # Nombre de función basado en sección
    func_name = f"calc_{section.replace('.', '_').replace('-', '_')}"
    
    # Simplificaciones comunes
    python_expr = latex
    python_expr = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', python_expr)
    python_expr = re.sub(r'\\sqrt\{([^}]+)\}', r'math.sqrt(\1)', python_expr)
    python_expr = re.sub(r'\\times', '*', python_expr)
    python_expr = re.sub(r'\\cdot', '*', python_expr)
    python_expr = re.sub(r'\^', '**', python_expr)
    python_expr = re.sub(r'[{}]', '', python_expr)
    
    # Crear función
    params = ", ".join(variables.keys())
    
    return f"def {func_name}({params}):\n    return {python_expr}"


def extract_subsections(content: str) -> list:
    """
    Extrae subsecciones marcadas con (a), (b), (c), etc.
    """
    subsections = []
    
    # Patrón: (a) texto hasta (b) o fin
    pattern = r'\(([a-z])\)\s*(.+?)(?=\([a-z]\)|$)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for letter, text in matches:
        text = text.strip()
        if len(text) > 10:  # Ignorar muy cortos
            subsections.append({
                "letter": letter,
                "content": text[:500]  # Limitar longitud
            })
    
    return subsections


def enrich_formulas():
    """Enriquece fórmulas con variables y funciones Python."""
    
    print("\n📐 Enriqueciendo fórmulas...")
    
    result = db.table("kg_nodes").select("id, section_path, formula_latex").eq("type", "FORMULA").execute()
    
    enriched = 0
    for node in result.data:
        latex = node.get("formula_latex")
        if not latex:
            continue
        
        # Parsear variables
        variables = parse_formula_variables(latex)
        
        if variables:
            # Generar Python
            python_func = generate_python_function(latex, variables, node.get("section_path", "unknown"))
            
            # Actualizar nodo
            db.table("kg_nodes").update({
                "formula_variables": variables,
                "formula_python": python_func
            }).eq("id", node["id"]).execute()
            
            enriched += 1
    
    print(f"   ✓ {enriched} fórmulas enriquecidas")


def enrich_sections_from_extraction():
    """
    Re-carga contenido completo de las extracciones originales.
    """
    print("\n📝 Enriqueciendo secciones desde extracciones...")
    
    updates = 0
    
    for f in sorted(EXTRACTED_DIR.glob("page_*.json")):
        with open(f) as file:
            data = json.load(file)
        
        for elem in data.get("elements", []):
            section_path = elem.get("section_path")
            if not section_path:
                continue
            
            title = elem.get("title")
            content = elem.get("content")
            elem_type = elem.get("type", "SECTION")
            
            # Buscar nodo existente
            result = db.table("kg_nodes").select("id, title, content").eq(
                "section_path", section_path
            ).eq("type", elem_type).limit(1).execute()
            
            if result.data:
                node = result.data[0]
                update_data = {}
                
                # Agregar título si falta
                if not node.get("title") and title:
                    update_data["title"] = title
                
                # Agregar contenido si falta o es más corto
                if content:
                    existing_content = node.get("content") or ""
                    if len(content) > len(existing_content):
                        update_data["content"] = content[:5000]
                
                if update_data:
                    db.table("kg_nodes").update(update_data).eq("id", node["id"]).execute()
                    updates += 1
    
    print(f"   ✓ {updates} nodos actualizados")


def create_subsection_nodes():
    """
    Crea nodos para subsecciones (a), (b), (c) dentro de secciones.
    """
    print("\n🔤 Creando nodos para subsecciones (a), (b), (c)...")
    
    # Buscar secciones con subsecciones
    result = db.table("kg_nodes").select("id, section_path, content").eq("type", "SECTION").execute()
    
    created = 0
    
    for node in result.data:
        content = node.get("content") or ""
        section_path = node.get("section_path")
        
        if not section_path:
            continue
        
        subsections = extract_subsections(content)
        
        for sub in subsections:
            sub_path = f"{section_path}({sub['letter']})"
            
            # Verificar si ya existe
            existing = db.table("kg_nodes").select("id").eq("section_path", sub_path).limit(1).execute()
            if existing.data:
                continue
            
            # Crear nuevo nodo
            new_node = {
                "id": str(uuid4()),
                "type": "SUBSECTION",
                "norm_code": "NSR-10",
                "section_path": sub_path,
                "hierarchy_depth": section_path.count('.') + 3,
                "content": sub["content"],
            }
            
            db.table("kg_nodes").insert(new_node).execute()
            
            # Crear arista CONTAINS
            edge = {
                "id": str(uuid4()),
                "source_id": node["id"],
                "target_id": new_node["id"],
                "edge_type": "CONTAINS"
            }
            db.table("kg_edges").insert(edge).execute()
            
            created += 1
    
    print(f"   ✓ {created} subsecciones creadas")


def link_figures_to_images():
    """
    Asegura que todas las figuras tengan URL de imagen.
    """
    print("\n🖼️ Vinculando figuras con imágenes...")
    
    # Cargar índice de figuras
    figures_index = EXTRACTED_DIR / "figures" / "precise" / "index.json"
    if not figures_index.exists():
        print("   ⚠️ No se encontró índice de figuras")
        return
    
    with open(figures_index) as f:
        figures = json.load(f)
    
    updated = 0
    
    for fig in figures:
        section = fig.get("id")
        filename = fig.get("filename")
        
        if not section or not filename:
            continue
        
        # URL pública
        public_url = f"https://vdakfewjadwaczulcmvj.supabase.co/storage/v1/object/public/figures/nsr10/titulo_a/{filename}"
        
        # Buscar nodo
        result = db.table("kg_nodes").select("id").eq("section_path", section).eq("type", "FIGURE").limit(1).execute()
        
        if result.data:
            db.table("kg_nodes").update({"source_pdf": public_url}).eq("id", result.data[0]["id"]).execute()
            updated += 1
    
    print(f"   ✓ {updated} figuras vinculadas")


def main():
    print("="*70)
    print("🔧 ENRIQUECIMIENTO DEL KNOWLEDGE GRAPH NSR-10")
    print("="*70)
    
    # 1. Enriquecer secciones desde extracciones
    enrich_sections_from_extraction()
    
    # 2. Enriquecer fórmulas
    enrich_formulas()
    
    # 3. Crear subsecciones
    create_subsection_nodes()
    
    # 4. Vincular figuras
    link_figures_to_images()
    
    print("\n" + "="*70)
    print("✅ ENRIQUECIMIENTO COMPLETADO")
    print("="*70)


if __name__ == "__main__":
    main()
