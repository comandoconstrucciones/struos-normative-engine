#!/usr/bin/env python3
"""
Extracción de Knowledge Graph para NSR-10 Título C (Concreto Estructural)
"""
import os
import json
import uuid

nodes = []
edges = []

def add_node(node_id, label, tipo, contenido="", metadata=None):
    nodes.append({
        "id": node_id,
        "label": label,
        "tipo": tipo,
        "contenido": contenido,
        "metadata": metadata or {}
    })

def add_edge(source, target, relation):
    edges.append({
        "source": source,
        "target": target,
        "relation": relation
    })

# ============================================
# TÍTULO Y CAPÍTULOS
# ============================================

add_node("titulo_c", "Título C: Concreto Estructural", "titulo", 
         "Requisitos para diseño y construcción de elementos de concreto estructural según ACI 318")

capitulos = [
    ("C.1", "General", "Alcance, planos, especificaciones, supervisión técnica"),
    ("C.2", "Notación y Definiciones", "Símbolos y terminología del diseño en concreto"),
    ("C.3", "Materiales", "Cemento, agregados, agua, acero de refuerzo, aditivos"),
    ("C.4", "Requisitos de Durabilidad", "Clases de exposición, protección contra corrosión y sulfatos"),
    ("C.5", "Calidad del Concreto", "f'c, f'cr, mezclas de prueba, control de calidad"),
    ("C.6", "Formaletas y Cimbras", "Diseño, remoción, requisitos de soporte"),
    ("C.7", "Detalles del Refuerzo", "Ganchos, doblado, recubrimiento, espaciamiento"),
    ("C.8", "Análisis y Diseño", "Métodos de análisis, redistribución de momentos"),
    ("C.9", "Requisitos de Resistencia", "Resistencia requerida, factores φ, deflexiones"),
    ("C.10", "Flexión y Carga Axial", "Diseño de vigas, columnas, elementos a flexocompresión"),
    ("C.11", "Cortante y Torsión", "Diseño por cortante, punzonamiento, torsión"),
    ("C.12", "Desarrollo y Empalmes", "Longitudes de desarrollo, traslapos, anclajes"),
    ("C.13", "Sistemas de Losa", "Losas en dos direcciones, método directo, pórtico equivalente"),
    ("C.14", "Muros", "Diseño de muros de corte, muros de contención"),
    ("C.15", "Cimentaciones", "Zapatas, pedestales, pilotes, muros de cimentación"),
    ("C.18", "Concreto Preesforzado", "Pretensado, postensado, pérdidas, esfuerzos admisibles"),
    ("C.19", "Cáscaras y Láminas", "Estructuras especiales tipo membrana"),
    ("C.21", "Diseño Sísmico", "DES, DMO, DMI, pórticos especiales, muros especiales"),
]

for cap_id, cap_nombre, cap_desc in capitulos:
    add_node(f"cap_{cap_id}", f"Capítulo {cap_id}: {cap_nombre}", "capitulo", cap_desc)
    add_edge("titulo_c", f"cap_{cap_id}", "contiene")

# ============================================
# CONCEPTOS DE MATERIALES
# ============================================

materiales = [
    ("fc", "f'c - Resistencia especificada", "Resistencia a compresión especificada del concreto a 28 días, MPa"),
    ("fcr", "f'cr - Resistencia promedio requerida", "Resistencia promedio para dosificación de mezcla"),
    ("fy", "fy - Fluencia del acero", "Esfuerzo de fluencia especificado del refuerzo, típico 420 MPa"),
    ("ec", "Ec - Módulo de elasticidad", "Módulo de elasticidad del concreto, Ec = 4700√f'c MPa"),
    ("es", "Es - Módulo del acero", "Módulo de elasticidad del acero de refuerzo, 200,000 MPa"),
]

for mat_id, mat_nombre, mat_desc in materiales:
    add_node(f"mat_{mat_id}", mat_nombre, "propiedad_material", mat_desc)
    add_edge("cap_C.3", f"mat_{mat_id}", "define")

# ============================================
# CLASES DE EXPOSICIÓN
# ============================================

exposiciones = [
    ("F", "Congelamiento y deshielo", "F0, F1, F2, F3"),
    ("S", "Sulfatos", "S0, S1, S2, S3"),
    ("P", "Permeabilidad", "P0, P1"),
    ("C", "Corrosión por cloruros", "C0, C1, C2"),
]

for exp_id, exp_nombre, exp_clases in exposiciones:
    add_node(f"exp_{exp_id}", f"Exposición {exp_id}: {exp_nombre}", "clase_exposicion", f"Clases: {exp_clases}")
    add_edge("cap_C.4", f"exp_{exp_id}", "clasifica")

# ============================================
# FACTORES DE REDUCCIÓN PHI
# ============================================

factores_phi = [
    ("traccion", "φ = 0.90", "Secciones controladas por tracción"),
    ("compresion_espiral", "φ = 0.75", "Compresión con refuerzo en espiral"),
    ("compresion_otros", "φ = 0.65", "Compresión con estribos"),
    ("cortante", "φ = 0.75", "Cortante y torsión"),
    ("aplastamiento", "φ = 0.65", "Aplastamiento del concreto"),
]

for phi_id, phi_valor, phi_desc in factores_phi:
    add_node(f"phi_{phi_id}", phi_valor, "factor_phi", phi_desc)
    add_edge("cap_C.9", f"phi_{phi_id}", "establece")

# ============================================
# ELEMENTOS ESTRUCTURALES
# ============================================

elementos = [
    ("viga", "Vigas", "Elementos sometidos principalmente a flexión"),
    ("columna", "Columnas", "Elementos sometidos a compresión y flexión"),
    ("losa", "Losas", "Elementos planos horizontales"),
    ("muro", "Muros", "Elementos verticales planos"),
    ("zapata", "Zapatas", "Cimentaciones superficiales"),
    ("pilote", "Pilotes", "Cimentaciones profundas"),
]

for elem_id, elem_nombre, elem_desc in elementos:
    add_node(f"elem_{elem_id}", elem_nombre, "elemento_estructural", elem_desc)
    
# Relaciones elementos con capítulos
add_edge("cap_C.10", "elem_viga", "diseña")
add_edge("cap_C.10", "elem_columna", "diseña")
add_edge("cap_C.13", "elem_losa", "diseña")
add_edge("cap_C.14", "elem_muro", "diseña")
add_edge("cap_C.15", "elem_zapata", "diseña")
add_edge("cap_C.15", "elem_pilote", "diseña")

# ============================================
# CUANTÍAS
# ============================================

cuantias = [
    ("rho_min_viga", "ρmin vigas", "0.25√f'c/fy ≥ 1.4/fy"),
    ("rho_max_viga", "ρmax vigas", "0.75ρb para secciones controladas por tracción"),
    ("rho_columna", "ρg columnas", "0.01 ≤ ρg ≤ 0.08"),
    ("rho_muro_vert", "ρℓ muros vertical", "≥ 0.0025"),
    ("rho_muro_horiz", "ρt muros horizontal", "≥ 0.0025"),
    ("rho_losa", "ρmin losas", "0.0018 para fy=420 MPa"),
]

for cuant_id, cuant_nombre, cuant_valor in cuantias:
    add_node(f"cuant_{cuant_id}", cuant_nombre, "cuantia", cuant_valor)
    add_edge("cap_C.10", f"cuant_{cuant_id}", "requiere")

# ============================================
# REQUISITOS SÍSMICOS
# ============================================

sismico = [
    ("des", "DES - Disipación Especial", "Pórticos y muros especiales para zonas de alta sismicidad"),
    ("dmo", "DMO - Disipación Moderada", "Requisitos intermedios para zonas de sismicidad moderada"),
    ("dmi", "DMI - Disipación Mínima", "Requisitos básicos para zonas de baja sismicidad"),
]

for sis_id, sis_nombre, sis_desc in sismico:
    add_node(f"sis_{sis_id}", sis_nombre, "categoria_sismica", sis_desc)
    add_edge("cap_C.21", f"sis_{sis_id}", "define")

# ============================================
# TABLAS NORMATIVAS
# ============================================

tablas = [
    ("C.4.2.1", "Categorías y clases de exposición", "nsr10_exposicion_concreto"),
    ("C.4.3.1", "Requisitos por clase de exposición", "nsr10_requisitos_concreto"),
    ("C.4.4.1", "Contenido de aire", "nsr10_aire_concreto"),
    ("C.5.3.2", "Resistencia promedio f'cr", "nsr10_fcr"),
    ("C.7.2", "Diámetros de doblado", "nsr10_doblado_barras"),
    ("C.7.7.1", "Recubrimientos mínimos", "nsr10_recubrimientos"),
    ("C.9.3.2", "Factores φ", "nsr10_phi_concreto"),
    ("C.9.5(a)", "Espesores mínimos", "nsr10_espesores_minimos"),
    ("C.9.5(b)", "Deflexiones admisibles", "nsr10_deflexiones"),
]

for tabla_id, tabla_nombre, sql_table in tablas:
    node_id = f"tabla_{tabla_id.replace('.', '_').replace('(', '').replace(')', '')}"
    add_node(node_id, f"Tabla {tabla_id}: {tabla_nombre}", "tabla", f"SQL: {sql_table}")
    add_edge("titulo_c", node_id, "contiene")

# ============================================
# FÓRMULAS PRINCIPALES
# ============================================

formulas = [
    ("Mn", "Momento nominal", "Mn = As × fy × (d - a/2)", "Flexión simple"),
    ("Vn", "Cortante nominal", "Vn = Vc + Vs", "Cortante"),
    ("Vc", "Cortante del concreto", "Vc = 0.17√f'c × bw × d", "Contribución del concreto"),
    ("Vs", "Cortante del acero", "Vs = Av × fy × d / s", "Contribución de estribos"),
    ("ld", "Longitud de desarrollo", "ld = db × fy / (1.7√f'c)", "Barras a tracción"),
    ("Ec", "Módulo de elasticidad", "Ec = 4700√f'c", "En MPa"),
]

for form_id, form_nombre, form_expr, form_desc in formulas:
    add_node(f"formula_{form_id}", form_nombre, "formula", f"{form_expr}\n{form_desc}")
    add_edge("cap_C.10", f"formula_{form_id}", "usa")

# ============================================
# GUARDAR
# ============================================

output_dir = "/root/clawd/leonardo/projects/normative-engine/kg"
os.makedirs(output_dir, exist_ok=True)

with open(f"{output_dir}/nodes_titulo_c.json", "w") as f:
    json.dump(nodes, f, indent=2, ensure_ascii=False)

with open(f"{output_dir}/edges_titulo_c.json", "w") as f:
    json.dump(edges, f, indent=2, ensure_ascii=False)

print(f"✓ Knowledge Graph Título C generado")
print(f"  - Nodos: {len(nodes)}")
print(f"  - Edges: {len(edges)}")
