#!/usr/bin/env python3
"""
Extracción de Knowledge Graph para NSR-10 Título B (Cargas)
"""
import os
import json
import hashlib
from datetime import datetime

# Nodos del Knowledge Graph - Título B
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

def add_edge(source, target, relation, metadata=None):
    edges.append({
        "source": source,
        "target": target,
        "relation": relation,
        "metadata": metadata or {}
    })

# ============================================
# CAPÍTULOS Y SECCIONES
# ============================================

capitulos = [
    ("B.1", "Requisitos Generales", "Define alcance, requisitos básicos, integridad estructural y trayectorias de carga"),
    ("B.2", "Combinaciones de Carga", "Combinaciones para métodos de esfuerzos de trabajo (ASD) y resistencia (LRFD)"),
    ("B.3", "Cargas Muertas", "Masas de materiales, cargas de elementos no estructurales horizontales y verticales"),
    ("B.4", "Cargas Vivas", "Cargas vivas mínimas por ocupación, reducción, impacto, empozamiento"),
    ("B.5", "Cargas de Suelo", "Empuje en muros de contención, subpresión, suelos expansivos, zonas inundables"),
    ("B.6", "Fuerzas de Viento", "Procedimiento simplificado y analítico, velocidad básica, exposición, presiones"),
]

for cap_id, cap_nombre, cap_desc in capitulos:
    add_node(f"cap_{cap_id}", f"Capítulo {cap_id}: {cap_nombre}", "capitulo", cap_desc)

# Conectar capítulos al título
add_node("titulo_b", "Título B: Cargas", "titulo", "Requisitos mínimos de cargas para diseño estructural diferentes al sismo")
for cap_id, _, _ in capitulos:
    add_edge("titulo_b", f"cap_{cap_id}", "contiene")

# ============================================
# TIPOS DE CARGA (Conceptos Fundamentales)
# ============================================

tipos_carga = [
    ("D", "Carga Muerta", "Cargas permanentes: estructura, muros, pisos, cubiertas, equipos fijos, preesfuerzo"),
    ("L", "Carga Viva", "Cargas por uso y ocupación de la edificación"),
    ("Lr", "Carga Viva Cubierta", "Cargas vivas en cubiertas incluyendo mantenimiento"),
    ("W", "Carga de Viento", "Fuerzas laterales y de succión por viento"),
    ("E", "Carga Sísmica", "Fuerzas sísmicas reducidas de diseño (del Título A)"),
    ("H", "Carga de Suelo", "Peso y presión del suelo, agua en el suelo"),
    ("F", "Carga de Fluidos", "Presión y peso de fluidos con densidades definidas"),
    ("T", "Efectos Diferidos", "Asentamientos, flujo plástico, retracción, temperatura"),
    ("G", "Carga de Granizo", "Acumulación de granizo en cubiertas"),
    ("R", "Carga de Lluvia", "Empozamiento de agua en cubiertas"),
]

for carga_id, carga_nombre, carga_desc in tipos_carga:
    add_node(f"carga_{carga_id}", f"{carga_id} - {carga_nombre}", "tipo_carga", carga_desc)
    add_edge("cap_B.2", f"carga_{carga_id}", "define")

# ============================================
# COMBINACIONES DE CARGA LRFD (B.2.4.2)
# ============================================

combinaciones_lrfd = [
    ("1", "1.4D", "Solo carga muerta"),
    ("2", "1.2D + 1.6L + 0.5(Lr o G o R)", "Carga muerta + viva predominante"),
    ("3", "1.2D + 1.6(Lr o G o R) + (0.5L o 0.8W)", "Carga de cubierta predominante"),
    ("4", "1.2D + 1.6W + 0.5L + 0.5(Lr o G o R)", "Carga de viento predominante"),
    ("5", "1.2D + 1.0E + 0.5L", "Carga sísmica"),
    ("6", "0.9D + 1.6W", "Volteo por viento"),
    ("7", "0.9D + 1.0E", "Volteo por sismo"),
]

for comb_num, comb_formula, comb_desc in combinaciones_lrfd:
    node_id = f"comb_lrfd_{comb_num}"
    add_node(node_id, f"Combinación B.2.4-{comb_num}", "combinacion", f"{comb_formula}\n{comb_desc}")
    add_edge("cap_B.2", node_id, "establece")

# ============================================
# CATEGORÍAS DE OCUPACIÓN (Cargas Vivas)
# ============================================

ocupaciones = [
    ("reunion", "Reunión", "Teatros, iglesias, gimnasios, estadios", 5.0),
    ("oficinas", "Oficinas", "Oficinas, restaurantes, corredores", 2.0),
    ("educativos", "Educativos", "Salones de clase, bibliotecas", 2.0),
    ("fabricas", "Fábricas", "Industrias livianas y pesadas", 5.0),
    ("institucional", "Institucional", "Hospitales, cárceles, guarderías", 2.0),
    ("comercio", "Comercio", "Tiendas minoristas y mayoristas", 5.0),
    ("residencial", "Residencial", "Viviendas, cuartos privados", 1.8),
    ("almacenamiento", "Almacenamiento", "Bodegas livianas y pesadas", 6.0),
    ("garajes", "Garajes", "Estacionamientos de vehículos", 2.5),
    ("coliseos", "Coliseos y Estadios", "Graderías, eventos masivos", 5.0),
]

for ocup_id, ocup_nombre, ocup_desc, carga_tipica in ocupaciones:
    node_id = f"ocup_{ocup_id}"
    add_node(node_id, ocup_nombre, "ocupacion", f"{ocup_desc}\nCarga típica: {carga_tipica} kN/m²")
    add_edge("cap_B.4", node_id, "clasifica")
    add_edge(node_id, "carga_L", "determina")

# ============================================
# MATERIALES (Densidades B.3.2-1)
# ============================================

materiales_principales = [
    ("acero", "Acero", 7800),
    ("concreto_simple", "Concreto Simple", 2300),
    ("concreto_reforzado", "Concreto Reforzado", 2400),
    ("mamposteria_arcilla", "Mampostería de Arcilla", 1850),
    ("mamposteria_concreto", "Mampostería de Concreto", 2150),
    ("madera", "Madera Seca", 600),
    ("vidrio", "Vidrio", 2600),
    ("agua", "Agua", 1000),
]

for mat_id, mat_nombre, densidad in materiales_principales:
    node_id = f"mat_{mat_id}"
    add_node(node_id, mat_nombre, "material", f"Densidad: {densidad} kg/m³")
    add_edge("cap_B.3", node_id, "tabula")
    add_edge(node_id, "carga_D", "contribuye_a")

# ============================================
# ELEMENTOS NO ESTRUCTURALES
# ============================================

elementos_ne = [
    ("cielo_raso", "Cielo Raso", "horizontal", "Canales, ductos, entramados, pañetes"),
    ("relleno_piso", "Relleno de Piso", "horizontal", "Arena, concreto, morteros"),
    ("acabados_piso", "Acabados de Piso", "horizontal", "Baldosas, terrazzo, madera"),
    ("cubiertas", "Elementos de Cubierta", "horizontal", "Tejas, membranas, aislantes"),
    ("particiones", "Particiones", "vertical", "Muros divisorios, drywall"),
    ("fachadas", "Fachadas", "vertical", "Muros cortina, enchapes"),
    ("muros", "Muros No Estructurales", "vertical", "Mampostería, paneles"),
]

for elem_id, elem_nombre, orientacion, elem_desc in elementos_ne:
    node_id = f"elem_{elem_id}"
    add_node(node_id, elem_nombre, "elemento_ne", f"Orientación: {orientacion}\n{elem_desc}")
    add_edge("cap_B.3", node_id, "regula")
    add_edge(node_id, "carga_D", "genera")

# ============================================
# EXPOSICIÓN AL VIENTO (B.6.5.6)
# ============================================

exposiciones_viento = [
    ("B", "Exposición B", "Áreas urbanas y suburbanas, terreno boscoso", 7.0, 365.8),
    ("C", "Exposición C", "Terreno abierto con obstrucciones dispersas <9m", 9.5, 274.3),
    ("D", "Exposición D", "Terreno plano sin obstrucciones, costas, zonas inundables", 11.5, 213.4),
]

for exp_id, exp_nombre, exp_desc, alpha, zg in exposiciones_viento:
    node_id = f"exp_{exp_id}"
    add_node(node_id, exp_nombre, "exposicion_viento", f"{exp_desc}\nα={alpha}, Zg={zg}m")
    add_edge("cap_B.6", node_id, "define")
    add_edge(node_id, "carga_W", "modifica")

# ============================================
# CATEGORÍAS DE EDIFICACIONES (Factor I viento)
# ============================================

categorias_edificacion = [
    ("I", "Categoría I", "Edificaciones temporales, agrícolas", 0.87),
    ("II", "Categoría II", "Edificaciones normales", 1.00),
    ("III", "Categoría III", "Edificaciones de alta ocupación", 1.15),
    ("IV", "Categoría IV", "Edificaciones esenciales", 1.15),
]

for cat_id, cat_nombre, cat_desc, factor_i in categorias_edificacion:
    node_id = f"cat_viento_{cat_id}"
    add_node(node_id, cat_nombre, "categoria_viento", f"{cat_desc}\nFactor I={factor_i}")
    add_edge("cap_B.6", node_id, "clasifica")

# ============================================
# TABLAS NORMATIVAS
# ============================================

tablas = [
    ("B.3.2-1", "Masas de los Materiales", "cap_B.3", "nsr10_masas_materiales"),
    ("B.3.4.1-1", "Cargas Muertas - Cielo Raso", "cap_B.3", "nsr10_cargas_elementos"),
    ("B.3.4.1-2", "Cargas Muertas - Relleno Pisos", "cap_B.3", "nsr10_cargas_elementos"),
    ("B.3.4.1-3", "Cargas Muertas - Pisos", "cap_B.3", "nsr10_cargas_elementos"),
    ("B.3.4.1-4", "Cargas Muertas - Cubiertas", "cap_B.3", "nsr10_cargas_elementos"),
    ("B.3.4.2-1", "Cargas Muertas - Recubrimiento Muros", "cap_B.3", "nsr10_cargas_elementos"),
    ("B.3.4.2-2", "Cargas Muertas - Particiones", "cap_B.3", "nsr10_cargas_elementos"),
    ("B.3.4.2-3", "Cargas Muertas - Enchapes", "cap_B.3", "nsr10_cargas_elementos"),
    ("B.3.4.2-4", "Cargas Muertas - Muros", "cap_B.3", "nsr10_cargas_elementos"),
    ("B.3.4.2-5", "Cargas Muertas - Ventanas", "cap_B.3", "nsr10_cargas_elementos"),
    ("B.3.4.3-1", "Valores Alternativos Carga Muerta", "cap_B.3", "nsr10_cargas_muertas"),
    ("B.4.2.1-1", "Cargas Vivas Mínimas", "cap_B.4", "nsr10_cargas_vivas"),
    ("B.4.2.1-2", "Cargas Vivas en Cubiertas", "cap_B.4", "nsr10_cargas_cubiertas"),
    ("B.6.5-1", "Factor de Importancia I (Viento)", "cap_B.6", "nsr10_viento"),
    ("B.6.5-2", "Constantes de Exposición", "cap_B.6", "nsr10_exposicion_viento"),
    ("B.6.5-3", "Coeficientes Kh y Kz", "cap_B.6", "nsr10_coef_kz"),
    ("B.6.5-4", "Factor Kd Direccionalidad", "cap_B.6", "nsr10_viento"),
]

for tabla_id, tabla_nombre, cap_ref, sql_table in tablas:
    node_id = f"tabla_{tabla_id.replace('.', '_').replace('-', '_')}"
    add_node(node_id, f"Tabla {tabla_id}: {tabla_nombre}", "tabla", f"SQL: {sql_table}")
    add_edge(cap_ref, node_id, "contiene")

# ============================================
# FÓRMULAS PRINCIPALES
# ============================================

formulas = [
    ("reduccion_L", "Reducción Carga Viva", "L = Lo × (0.25 + 4.57/√AI)", "B.4.5.1", "AI = área de influencia ≥ 37m²"),
    ("presion_q", "Presión por Velocidad", "qz = 0.613 × Kz × Kzt × Kd × V² × I", "B.6.5.10", "qz en N/m², V en m/s"),
    ("kz_formula", "Coeficiente Kz", "Kz = 2.01 × (z/Zg)^(2/α)", "B.6.5-3", "Para z ≥ 4.0m"),
    ("presion_viento", "Presión de Viento", "p = q × G × Cp - qi × (GCpi)", "B.6.5.12", "G=factor ráfaga, Cp=coef presión"),
]

for form_id, form_nombre, form_expr, form_ref, form_notas in formulas:
    node_id = f"formula_{form_id}"
    add_node(node_id, form_nombre, "formula", f"{form_expr}\nRef: {form_ref}\n{form_notas}")
    
# Relaciones entre fórmulas y conceptos
add_edge("formula_reduccion_L", "carga_L", "calcula")
add_edge("formula_presion_q", "carga_W", "calcula")
add_edge("formula_kz_formula", "exp_B", "usa")
add_edge("formula_kz_formula", "exp_C", "usa")
add_edge("formula_kz_formula", "exp_D", "usa")

# ============================================
# RELACIONES CRUZADAS CON TÍTULO A
# ============================================

# Conexiones con Título A (sismo)
add_node("titulo_a_ref", "Título A: Sismo Resistencia", "referencia", "Referencia cruzada al Título A")
add_edge("carga_E", "titulo_a_ref", "definido_en")
add_edge("comb_lrfd_5", "titulo_a_ref", "usa_de")
add_edge("comb_lrfd_7", "titulo_a_ref", "usa_de")

# Grupo de uso (del Título A)
grupos_uso = [
    ("I", "Ocupación Normal", "Edificaciones de ocupación normal"),
    ("II", "Ocupación Especial", "Reuniones >500 personas, comercio >500m²"),
    ("III", "Atención a la Comunidad", "Colegios, universidades, guarderías"),
    ("IV", "Indispensables", "Hospitales, bomberos, telecomunicaciones"),
]

for grupo_id, grupo_nombre, grupo_desc in grupos_uso:
    node_id = f"grupo_{grupo_id}"
    add_node(node_id, f"Grupo {grupo_id}: {grupo_nombre}", "grupo_uso", grupo_desc)
    add_edge("titulo_a_ref", node_id, "clasifica")
    # Relación con categorías de viento (misma clasificación)
    add_edge(node_id, f"cat_viento_{grupo_id}", "equivale")

# ============================================
# GUARDAR RESULTADOS
# ============================================

output_dir = "/root/clawd/leonardo/projects/normative-engine/kg"
os.makedirs(output_dir, exist_ok=True)

# Guardar nodos
with open(f"{output_dir}/nodes_titulo_b.json", "w") as f:
    json.dump(nodes, f, indent=2, ensure_ascii=False)

# Guardar edges
with open(f"{output_dir}/edges_titulo_b.json", "w") as f:
    json.dump(edges, f, indent=2, ensure_ascii=False)

print(f"✓ Knowledge Graph Título B generado")
print(f"  - Nodos: {len(nodes)}")
print(f"  - Edges: {len(edges)}")
print(f"  - Output: {output_dir}")
