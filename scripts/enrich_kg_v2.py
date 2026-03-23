"""
enrich_kg_v2.py — Enriquece el Knowledge Graph de NSR-10:
1. Conecta DEFINITIONS al glosario con aristas DEFINES
2. Genera funciones Python ejecutables para cada FORMULA
3. Agrega validaciones y tests unitarios
"""

import json
import os
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Supabase
from supabase import create_client, Client

SUPABASE_URL = "https://vdakfewjadwaczulcmvj.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

@dataclass
class FormulaFunction:
    """Función Python para una fórmula NSR-10."""
    formula_id: str
    section_path: str
    name: str  # nombre de función: calc_Sa, calc_T, etc.
    docstring: str
    parameters: List[Dict]  # [{name, type, description, unit}]
    returns: Dict  # {type, description, unit}
    code: str  # código Python ejecutable
    test_cases: List[Dict]  # [{inputs, expected, tolerance}]


# ============================================================
# GLOSARIO NSR-10 — Definiciones clave
# ============================================================
GLOSARIO_NSR10 = {
    # Parámetros sísmicos
    "Aa": {
        "term": "Aa",
        "definition": "Coeficiente que representa la aceleración horizontal pico efectiva para diseño",
        "unit": "adimensional (fracción de g)",
        "section": "A.2.2",
        "related": ["Av", "Fa", "Fv", "zona_sismica"]
    },
    "Av": {
        "term": "Av", 
        "definition": "Coeficiente que representa la velocidad horizontal pico efectiva para diseño",
        "unit": "adimensional (fracción de g)",
        "section": "A.2.2",
        "related": ["Aa", "Fa", "Fv"]
    },
    "Fa": {
        "term": "Fa",
        "definition": "Coeficiente de amplificación que afecta la aceleración en la zona de periodos cortos, debido a los efectos de sitio",
        "unit": "adimensional",
        "section": "A.2.4",
        "table": "A.2.4-3",
        "related": ["Aa", "perfil_suelo"]
    },
    "Fv": {
        "term": "Fv",
        "definition": "Coeficiente de amplificación que afecta la aceleración en la zona de periodos intermedios, debido a los efectos de sitio",
        "unit": "adimensional", 
        "section": "A.2.4",
        "table": "A.2.4-4",
        "related": ["Av", "perfil_suelo"]
    },
    "I": {
        "term": "I",
        "definition": "Coeficiente de importancia de la edificación",
        "unit": "adimensional",
        "section": "A.2.5",
        "table": "A.2.5-1",
        "values": {"I": 1.0, "II": 1.0, "III": 1.25, "IV": 1.50}
    },
    
    # Periodos
    "T": {
        "term": "T",
        "definition": "Periodo fundamental de vibración de la edificación",
        "unit": "s",
        "section": "A.4.2"
    },
    "Ta": {
        "term": "Ta",
        "definition": "Periodo aproximado de vibración calculado con fórmulas empíricas",
        "unit": "s",
        "section": "A.4.2.1",
        "formula": "Ta = Ct × h^α"
    },
    "T0": {
        "term": "T0",
        "definition": "Periodo de vibración al cual inicia la zona de aceleraciones constantes del espectro",
        "unit": "s",
        "section": "A.2.6",
        "formula": "T0 = 0.1 × (Av×Fv)/(Aa×Fa)"
    },
    "TC": {
        "term": "TC",
        "definition": "Periodo de vibración correspondiente a la transición entre la zona de aceleración constante y la de velocidad constante",
        "unit": "s",
        "section": "A.2.6",
        "formula": "TC = 0.48 × (Av×Fv)/(Aa×Fa)"
    },
    "TL": {
        "term": "TL",
        "definition": "Periodo de vibración correspondiente al inicio de la zona de desplazamiento aproximadamente constante",
        "unit": "s",
        "section": "A.2.6",
        "formula": "TL = 2.4 × Fv"
    },
    "Cu": {
        "term": "Cu",
        "definition": "Coeficiente para calcular el límite superior del periodo fundamental",
        "unit": "adimensional",
        "section": "A.4.2.1",
        "table": "A.4.2-1"
    },
    
    # Respuesta estructural
    "Sa": {
        "term": "Sa",
        "definition": "Aceleración espectral de diseño expresada como fracción de la gravedad",
        "unit": "adimensional (fracción de g)",
        "section": "A.2.6"
    },
    "R": {
        "term": "R",
        "definition": "Coeficiente de capacidad de disipación de energía en el rango inelástico",
        "unit": "adimensional",
        "section": "A.3.3",
        "table": "A.3-1"
    },
    "R0": {
        "term": "R0",
        "definition": "Coeficiente de capacidad de disipación de energía básico para el sistema estructural",
        "unit": "adimensional",
        "section": "A.3.3",
        "table": "A.3-3"
    },
    "Ω0": {
        "term": "Ω0",
        "definition": "Coeficiente de sobrerresistencia",
        "unit": "adimensional",
        "section": "A.3.6",
        "table": "A.3-3"
    },
    "Cd": {
        "term": "Cd",
        "definition": "Coeficiente de amplificación de deflexiones",
        "unit": "adimensional", 
        "section": "A.6.3",
        "table": "A.3-3"
    },
    
    # Derivas
    "Δ": {
        "term": "Δ",
        "definition": "Deriva o desplazamiento horizontal relativo entre dos pisos consecutivos",
        "unit": "m o mm",
        "section": "A.6.3",
        "related": ["Δmax", "hpi"]
    },
    "Δmax": {
        "term": "Δmax",
        "definition": "Deriva máxima permitida como porcentaje de la altura del piso",
        "unit": "porcentaje de hpi",
        "section": "A.6.4.1",
        "table": "A.6.4-1"
    },
    "hpi": {
        "term": "hpi",
        "definition": "Altura del piso i",
        "unit": "m",
        "section": "A.6.4"
    },
    
    # Cortante
    "Vs": {
        "term": "Vs",
        "definition": "Cortante sísmico en la base de la estructura",
        "unit": "kN",
        "section": "A.4.3"
    },
    "k": {
        "term": "k",
        "definition": "Exponente relacionado con el periodo de la estructura para distribución de fuerzas",
        "unit": "adimensional",
        "section": "A.4.3"
    },
    
    # Perfiles de suelo
    "perfil_suelo": {
        "term": "Perfil de suelo",
        "definition": "Clasificación del suelo basada en los 30 m superiores del perfil",
        "unit": "letra A-F",
        "section": "A.2.4.1",
        "values": {"A": "Roca competente", "B": "Roca de rigidez media", "C": "Suelos muy densos o roca blanda", "D": "Suelos rígidos", "E": "Suelos blandos", "F": "Suelos especiales"}
    },
}


# ============================================================
# FÓRMULAS NSR-10 — Con funciones Python ejecutables
# ============================================================
FORMULAS_NSR10 = [
    # --- A.2 Zonas de amenaza sísmica ---
    FormulaFunction(
        formula_id="NSR10-A.2.6-1",
        section_path="A.2.6.1",
        name="calc_T0",
        docstring="Calcula el periodo T0 (inicio de la meseta del espectro) según A.2.6",
        parameters=[
            {"name": "Av", "type": "float", "description": "Coef. velocidad efectiva", "unit": "-"},
            {"name": "Fv", "type": "float", "description": "Coef. amplificación velocidad", "unit": "-"},
            {"name": "Aa", "type": "float", "description": "Coef. aceleración efectiva", "unit": "-"},
            {"name": "Fa", "type": "float", "description": "Coef. amplificación aceleración", "unit": "-"},
        ],
        returns={"type": "float", "description": "Periodo T0", "unit": "s"},
        code="""def calc_T0(Av: float, Fv: float, Aa: float, Fa: float) -> float:
    \"\"\"Calcula T0 según NSR-10 A.2.6: T0 = 0.1 × (Av×Fv)/(Aa×Fa)\"\"\"
    return 0.1 * (Av * Fv) / (Aa * Fa)""",
        test_cases=[
            {"inputs": {"Av": 0.20, "Fv": 1.65, "Aa": 0.15, "Fa": 1.20}, "expected": 0.183, "tolerance": 0.01},
            {"inputs": {"Av": 0.30, "Fv": 1.80, "Aa": 0.25, "Fa": 1.10}, "expected": 0.196, "tolerance": 0.01},
        ]
    ),
    FormulaFunction(
        formula_id="NSR10-A.2.6-2",
        section_path="A.2.6.1",
        name="calc_TC",
        docstring="Calcula el periodo TC (fin de la meseta) según A.2.6",
        parameters=[
            {"name": "Av", "type": "float", "description": "Coef. velocidad efectiva", "unit": "-"},
            {"name": "Fv", "type": "float", "description": "Coef. amplificación velocidad", "unit": "-"},
            {"name": "Aa", "type": "float", "description": "Coef. aceleración efectiva", "unit": "-"},
            {"name": "Fa", "type": "float", "description": "Coef. amplificación aceleración", "unit": "-"},
        ],
        returns={"type": "float", "description": "Periodo TC", "unit": "s"},
        code="""def calc_TC(Av: float, Fv: float, Aa: float, Fa: float) -> float:
    \"\"\"Calcula TC según NSR-10 A.2.6: TC = 0.48 × (Av×Fv)/(Aa×Fa)\"\"\"
    return 0.48 * (Av * Fv) / (Aa * Fa)""",
        test_cases=[
            {"inputs": {"Av": 0.20, "Fv": 1.65, "Aa": 0.15, "Fa": 1.20}, "expected": 0.88, "tolerance": 0.01},
            {"inputs": {"Av": 0.30, "Fv": 1.80, "Aa": 0.25, "Fa": 1.10}, "expected": 0.94, "tolerance": 0.01},
        ]
    ),
    FormulaFunction(
        formula_id="NSR10-A.2.6-3",
        section_path="A.2.6.2",
        name="calc_TL",
        docstring="Calcula el periodo TL (inicio de desplazamiento constante) según A.2.6",
        parameters=[
            {"name": "Fv", "type": "float", "description": "Coef. amplificación velocidad", "unit": "-"},
        ],
        returns={"type": "float", "description": "Periodo TL", "unit": "s"},
        code="""def calc_TL(Fv: float) -> float:
    \"\"\"Calcula TL según NSR-10 A.2.6: TL = 2.4 × Fv\"\"\"
    return 2.4 * Fv""",
        test_cases=[
            {"inputs": {"Fv": 1.65}, "expected": 3.96, "tolerance": 0.01},
            {"inputs": {"Fv": 2.40}, "expected": 5.76, "tolerance": 0.01},
        ]
    ),
    FormulaFunction(
        formula_id="NSR10-A.2.6-4",
        section_path="A.2.6.3",
        name="calc_Sa",
        docstring="Calcula la aceleración espectral Sa(T) según A.2.6",
        parameters=[
            {"name": "T", "type": "float", "description": "Periodo de vibración", "unit": "s"},
            {"name": "Aa", "type": "float", "description": "Coef. aceleración efectiva", "unit": "-"},
            {"name": "Fa", "type": "float", "description": "Coef. amplificación aceleración", "unit": "-"},
            {"name": "Av", "type": "float", "description": "Coef. velocidad efectiva", "unit": "-"},
            {"name": "Fv", "type": "float", "description": "Coef. amplificación velocidad", "unit": "-"},
            {"name": "I", "type": "float", "description": "Coef. de importancia", "unit": "-", "default": 1.0},
        ],
        returns={"type": "float", "description": "Aceleración espectral Sa", "unit": "g"},
        code="""def calc_Sa(T: float, Aa: float, Fa: float, Av: float, Fv: float, I: float = 1.0) -> float:
    \"\"\"Calcula Sa(T) según NSR-10 A.2.6\"\"\"
    # Periodos característicos
    T0 = 0.1 * (Av * Fv) / (Aa * Fa)
    TC = 0.48 * (Av * Fv) / (Aa * Fa)
    TL = 2.4 * Fv
    
    # Aceleración meseta
    Sa0 = 2.5 * Aa * Fa * I
    
    if T < T0:
        # Rampa ascendente
        return 2.5 * Aa * Fa * I * (0.4 + 0.6 * T / T0)
    elif T <= TC:
        # Meseta
        return Sa0
    elif T <= TL:
        # Rama descendente velocidad constante
        return 1.2 * Av * Fv * I / T
    else:
        # Rama descendente desplazamiento constante
        return 1.2 * Av * Fv * TL * I / (T ** 2)""",
        test_cases=[
            {"inputs": {"T": 0.0, "Aa": 0.15, "Fa": 1.20, "Av": 0.20, "Fv": 1.65, "I": 1.0}, "expected": 0.18, "tolerance": 0.02},
            {"inputs": {"T": 0.5, "Aa": 0.15, "Fa": 1.20, "Av": 0.20, "Fv": 1.65, "I": 1.0}, "expected": 0.45, "tolerance": 0.02},
            {"inputs": {"T": 1.0, "Aa": 0.15, "Fa": 1.20, "Av": 0.20, "Fv": 1.65, "I": 1.0}, "expected": 0.396, "tolerance": 0.02},
            {"inputs": {"T": 2.0, "Aa": 0.15, "Fa": 1.20, "Av": 0.20, "Fv": 1.65, "I": 1.0}, "expected": 0.198, "tolerance": 0.02},
        ]
    ),
    
    # --- A.4 Periodo fundamental ---
    FormulaFunction(
        formula_id="NSR10-A.4.2-1",
        section_path="A.4.2.1",
        name="calc_Ta",
        docstring="Calcula el periodo aproximado Ta según A.4.2.1",
        parameters=[
            {"name": "Ct", "type": "float", "description": "Coeficiente según sistema estructural", "unit": "-"},
            {"name": "h", "type": "float", "description": "Altura de la edificación", "unit": "m"},
            {"name": "alpha", "type": "float", "description": "Exponente según sistema", "unit": "-"},
        ],
        returns={"type": "float", "description": "Periodo aproximado Ta", "unit": "s"},
        code="""def calc_Ta(Ct: float, h: float, alpha: float) -> float:
    \"\"\"Calcula Ta según NSR-10 A.4.2.1: Ta = Ct × h^α\"\"\"
    return Ct * (h ** alpha)""",
        test_cases=[
            {"inputs": {"Ct": 0.047, "h": 30.0, "alpha": 0.90}, "expected": 1.00, "tolerance": 0.05},
            {"inputs": {"Ct": 0.072, "h": 20.0, "alpha": 0.80}, "expected": 0.79, "tolerance": 0.05},
        ]
    ),
    FormulaFunction(
        formula_id="NSR10-A.4.2-2",
        section_path="A.4.2.1",
        name="calc_T_limit",
        docstring="Calcula el límite superior del periodo T ≤ Cu × Ta",
        parameters=[
            {"name": "Cu", "type": "float", "description": "Coeficiente límite superior (Tabla A.4.2-1)", "unit": "-"},
            {"name": "Ta", "type": "float", "description": "Periodo aproximado", "unit": "s"},
        ],
        returns={"type": "float", "description": "Periodo máximo permitido", "unit": "s"},
        code="""def calc_T_limit(Cu: float, Ta: float) -> float:
    \"\"\"Calcula T máximo según NSR-10 A.4.2.1: T_limit = Cu × Ta\"\"\"
    return Cu * Ta""",
        test_cases=[
            {"inputs": {"Cu": 1.20, "Ta": 0.80}, "expected": 0.96, "tolerance": 0.01},
            {"inputs": {"Cu": 1.40, "Ta": 0.60}, "expected": 0.84, "tolerance": 0.01},
        ]
    ),
    
    # --- A.4.3 Cortante basal ---
    FormulaFunction(
        formula_id="NSR10-A.4.3-1",
        section_path="A.4.3",
        name="calc_Vs",
        docstring="Calcula el cortante sísmico en la base según A.4.3",
        parameters=[
            {"name": "Sa", "type": "float", "description": "Aceleración espectral", "unit": "g"},
            {"name": "g", "type": "float", "description": "Aceleración gravedad", "unit": "m/s²", "default": 9.81},
            {"name": "M", "type": "float", "description": "Masa total de la estructura", "unit": "kg"},
        ],
        returns={"type": "float", "description": "Cortante basal", "unit": "kN"},
        code="""def calc_Vs(Sa: float, M: float, g: float = 9.81) -> float:
    \"\"\"Calcula Vs según NSR-10 A.4.3: Vs = Sa × g × M / 1000 (en kN)\"\"\"
    return Sa * g * M / 1000""",
        test_cases=[
            {"inputs": {"Sa": 0.45, "M": 100000, "g": 9.81}, "expected": 441.45, "tolerance": 1.0},
        ]
    ),
    FormulaFunction(
        formula_id="NSR10-A.4.3-2",
        section_path="A.4.3.2",
        name="calc_k",
        docstring="Calcula el exponente k para distribución de fuerzas según A.4.3.2",
        parameters=[
            {"name": "T", "type": "float", "description": "Periodo fundamental", "unit": "s"},
        ],
        returns={"type": "float", "description": "Exponente k", "unit": "-"},
        code="""def calc_k(T: float) -> float:
    \"\"\"Calcula k según NSR-10 A.4.3.2\"\"\"
    if T <= 0.5:
        return 1.0
    elif T >= 2.5:
        return 2.0
    else:
        return 0.75 + 0.5 * T""",
        test_cases=[
            {"inputs": {"T": 0.3}, "expected": 1.0, "tolerance": 0.01},
            {"inputs": {"T": 1.0}, "expected": 1.25, "tolerance": 0.01},
            {"inputs": {"T": 2.0}, "expected": 1.75, "tolerance": 0.01},
            {"inputs": {"T": 3.0}, "expected": 2.0, "tolerance": 0.01},
        ]
    ),
    
    # --- A.6 Derivas ---
    FormulaFunction(
        formula_id="NSR10-A.6.3-1",
        section_path="A.6.3.1",
        name="calc_delta_inelastic",
        docstring="Calcula la deriva inelástica amplificada según A.6.3",
        parameters=[
            {"name": "delta_elastic", "type": "float", "description": "Deriva elástica del análisis", "unit": "m"},
            {"name": "Cd", "type": "float", "description": "Coef. amplificación deflexiones", "unit": "-"},
        ],
        returns={"type": "float", "description": "Deriva inelástica", "unit": "m"},
        code="""def calc_delta_inelastic(delta_elastic: float, Cd: float) -> float:
    \"\"\"Calcula deriva inelástica según NSR-10 A.6.3: Δinelástica = Cd × Δelástica\"\"\"
    return Cd * delta_elastic""",
        test_cases=[
            {"inputs": {"delta_elastic": 0.005, "Cd": 4.0}, "expected": 0.020, "tolerance": 0.001},
        ]
    ),
    FormulaFunction(
        formula_id="NSR10-A.6.4-1",
        section_path="A.6.4.1",
        name="check_drift_limit",
        docstring="Verifica si la deriva cumple con el límite de A.6.4.1",
        parameters=[
            {"name": "delta", "type": "float", "description": "Deriva del piso", "unit": "m"},
            {"name": "hpi", "type": "float", "description": "Altura del piso", "unit": "m"},
            {"name": "limit_pct", "type": "float", "description": "Límite de deriva", "unit": "%", "default": 1.0},
        ],
        returns={"type": "dict", "description": "Resultado de verificación", "unit": "-"},
        code="""def check_drift_limit(delta: float, hpi: float, limit_pct: float = 1.0) -> dict:
    \"\"\"Verifica deriva según NSR-10 A.6.4.1\"\"\"
    drift_ratio = delta / hpi
    limit = limit_pct / 100
    passed = drift_ratio <= limit
    margin = (limit - drift_ratio) / limit * 100 if passed else (drift_ratio - limit) / limit * 100
    
    return {
        "passed": passed,
        "drift_pct": round(drift_ratio * 100, 3),
        "limit_pct": limit_pct,
        "margin_pct": round(margin, 1),
        "status": "PASS" if passed else "FAIL"
    }""",
        test_cases=[
            {"inputs": {"delta": 0.025, "hpi": 3.0, "limit_pct": 1.0}, "expected": {"passed": True, "status": "PASS"}, "tolerance": None},
            {"inputs": {"delta": 0.035, "hpi": 3.0, "limit_pct": 1.0}, "expected": {"passed": False, "status": "FAIL"}, "tolerance": None},
        ]
    ),
    
    # --- A.3 Factores R ---
    FormulaFunction(
        formula_id="NSR10-A.3.3-1",
        section_path="A.3.3.4",
        name="calc_R",
        docstring="Calcula R considerando irregularidades según A.3.3.4",
        parameters=[
            {"name": "R0", "type": "float", "description": "R básico del sistema", "unit": "-"},
            {"name": "phi_a", "type": "float", "description": "Factor por irregularidad en altura", "unit": "-", "default": 1.0},
            {"name": "phi_p", "type": "float", "description": "Factor por irregularidad en planta", "unit": "-", "default": 1.0},
            {"name": "phi_r", "type": "float", "description": "Factor por ausencia de redundancia", "unit": "-", "default": 1.0},
        ],
        returns={"type": "float", "description": "R ajustado", "unit": "-"},
        code="""def calc_R(R0: float, phi_a: float = 1.0, phi_p: float = 1.0, phi_r: float = 1.0) -> float:
    \"\"\"Calcula R según NSR-10 A.3.3.4: R = R0 × φa × φp × φr\"\"\"
    return R0 * phi_a * phi_p * phi_r""",
        test_cases=[
            {"inputs": {"R0": 7.0, "phi_a": 0.9, "phi_p": 0.9, "phi_r": 1.0}, "expected": 5.67, "tolerance": 0.1},
            {"inputs": {"R0": 5.0, "phi_a": 1.0, "phi_p": 1.0, "phi_r": 0.75}, "expected": 3.75, "tolerance": 0.1},
        ]
    ),
]


def upload_glossary_to_kg(db: Client):
    """Sube el glosario como nodos tipo GLOSSARY_TERM y crea aristas DEFINES."""
    print("Subiendo glosario NSR-10...")
    
    for term_id, term_data in GLOSARIO_NSR10.items():
        # Crear nodo de glosario
        node = {
            "norm_code": "NSR-10",
            "node_type": "GLOSSARY_TERM",
            "section_path": term_data.get("section", "A.1.4"),
            "title": term_data["term"],
            "content": term_data["definition"],
            "metadata": {
                "unit": term_data.get("unit"),
                "table": term_data.get("table"),
                "formula": term_data.get("formula"),
                "values": term_data.get("values"),
                "related": term_data.get("related", [])
            }
        }
        
        # Insert o update
        result = db.table("kg_nodes").upsert(node, on_conflict="norm_code,section_path,title").execute()
        
        if result.data:
            node_id = result.data[0]["id"]
            print(f"  ✓ {term_data['term']}: {node_id}")
    
    print(f"  Total: {len(GLOSARIO_NSR10)} términos de glosario")


def upload_formulas_to_kg(db: Client):
    """Sube las fórmulas con código Python ejecutable."""
    print("\nSubiendo fórmulas con funciones Python...")
    
    for formula in FORMULAS_NSR10:
        node = {
            "norm_code": "NSR-10",
            "node_type": "FORMULA",
            "section_path": formula.section_path,
            "title": formula.name,
            "content": formula.docstring,
            "metadata": {
                "formula_id": formula.formula_id,
                "parameters": formula.parameters,
                "returns": formula.returns,
                "python_code": formula.code,
                "test_cases": formula.test_cases
            }
        }
        
        result = db.table("kg_nodes").upsert(node, on_conflict="norm_code,section_path,title").execute()
        
        if result.data:
            print(f"  ✓ {formula.name} ({formula.section_path})")
    
    print(f"  Total: {len(FORMULAS_NSR10)} fórmulas con código Python")


def run_formula_tests():
    """Ejecuta los tests de todas las fórmulas."""
    print("\n=== VALIDACIÓN DE FÓRMULAS ===")
    
    passed = 0
    failed = 0
    
    for formula in FORMULAS_NSR10:
        # Ejecutar el código para definir la función
        exec(formula.code, globals())
        func = globals()[formula.name]
        
        print(f"\n{formula.name} ({formula.formula_id}):")
        
        for i, test in enumerate(formula.test_cases):
            try:
                result = func(**test["inputs"])
                
                if test["tolerance"] is None:
                    # Comparación de diccionarios
                    expected = test["expected"]
                    if isinstance(result, dict):
                        test_pass = all(result.get(k) == v for k, v in expected.items())
                    else:
                        test_pass = result == expected
                else:
                    # Comparación numérica con tolerancia
                    test_pass = abs(result - test["expected"]) <= test["tolerance"]
                
                if test_pass:
                    passed += 1
                    print(f"  ✓ Test {i+1}: {test['inputs']} → {result}")
                else:
                    failed += 1
                    print(f"  ✗ Test {i+1}: {test['inputs']} → {result} (esperado: {test['expected']})")
            
            except Exception as e:
                failed += 1
                print(f"  ✗ Test {i+1}: ERROR - {e}")
    
    print(f"\n{'='*50}")
    print(f"RESULTADOS: {passed} pasaron, {failed} fallaron")
    print(f"{'='*50}")
    
    return passed, failed


def generate_formula_module():
    """Genera un módulo Python con todas las fórmulas."""
    module_code = '''"""
nsr10_formulas.py — Fórmulas NSR-10 como funciones Python ejecutables.

Generado automáticamente por enrich_kg_v2.py
Struos.AI - Motor Normativo NSR-10
"""

from typing import Dict, List, Optional

'''
    
    for formula in FORMULAS_NSR10:
        # Agregar docstring mejorado
        code_lines = formula.code.split('\n')
        func_def = code_lines[0]
        
        module_code += f"\n# {formula.formula_id} ({formula.section_path})\n"
        module_code += formula.code
        module_code += "\n"
    
    # Agregar función de conveniencia
    module_code += '''

# === Funciones de conveniencia ===

def spectrum_nsr10(Aa: float, Av: float, Fa: float, Fv: float, I: float = 1.0, T_max: float = 4.0, steps: int = 100) -> List[Dict]:
    """Genera el espectro de diseño NSR-10 completo."""
    import numpy as np
    
    T_values = np.linspace(0, T_max, steps)
    spectrum = []
    
    for T in T_values:
        Sa = calc_Sa(T, Aa, Fa, Av, Fv, I)
        spectrum.append({"T": round(T, 3), "Sa": round(Sa, 4)})
    
    return spectrum


def get_seismic_params_bogota() -> Dict:
    """Parámetros sísmicos para Bogotá (zona intermedia)."""
    return {
        "Aa": 0.15,
        "Av": 0.20,
        "Fa": 1.20,  # Suelo tipo D
        "Fv": 1.65,  # Suelo tipo D
        "I": 1.0,
        "zona": "Intermedia"
    }
'''
    
    return module_code


if __name__ == "__main__":
    import sys
    
    # Conectar a Supabase
    if SUPABASE_KEY:
        db = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"Conectado a Supabase: {SUPABASE_URL}")
    else:
        db = None
        print("⚠️ Sin SUPABASE_SERVICE_ROLE_KEY - modo test local")
    
    # Opción 1: Solo validar fórmulas
    if "--test" in sys.argv:
        run_formula_tests()
        sys.exit(0)
    
    # Opción 2: Generar módulo Python
    if "--generate" in sys.argv:
        module = generate_formula_module()
        output_path = "../src/nsr10_formulas.py"
        with open(output_path, "w") as f:
            f.write(module)
        print(f"Módulo generado: {output_path}")
        sys.exit(0)
    
    # Opción 3: Subir a Supabase
    if db:
        upload_glossary_to_kg(db)
        upload_formulas_to_kg(db)
        print("\n✅ Knowledge Graph enriquecido")
    
    # Siempre ejecutar tests
    run_formula_tests()
